import streamlit as st
from slack_bolt import App
import requests
import pytz
from datetime import datetime

def get_all_channels(bot_token):
    """Slack の全チャンネル（パブリック・プライベート）の一覧を取得"""
    all_channels = []
    cursor = None
    headers = {"Authorization": f"Bearer {bot_token}"}
    while True:
        params = {
            "limit": 200,
            "types": "public_channel,private_channel"
        }
        if cursor:
            params["cursor"] = cursor
        response = requests.get("https://slack.com/api/conversations.list", headers=headers, params=params)
        data = response.json()
        if not data.get("ok"):
            raise Exception(f"Slack API エラー (conversations.list): {data.get('error')}")
        all_channels.extend(data.get("channels", []))
        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return all_channels

def get_all_users(bot_token):
    """Slack の全ユーザー一覧を取得（DM送信用）"""
    all_users = []
    cursor = None
    headers = {"Authorization": f"Bearer {bot_token}"}
    while True:
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = requests.get("https://slack.com/api/users.list", headers=headers, params=params)
        data = response.json()
        if not data.get("ok"):
            raise Exception(f"Slack API エラー (users.list): {data.get('error')}")
        all_users.extend(data.get("members", []))
        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return all_users

def main():
    st.title("Slack 予約投稿アプリ（Streamlit版）")

    # --- Secrets からトークンを取得 ---
    #   Streamlit Cloud の [Secrets] タブで SLACK_BOT_TOKEN / SLACK_SIGNING_SECRET を設定しておく
    bot_token = st.secrets["SLACK_BOT_TOKEN"]
    signing_secret = st.secrets["SLACK_SIGNING_SECRET"]

    # --- 1) チャンネル・ユーザー一覧の取得ボタン ---
    if st.button("チャンネル・ユーザー一覧を取得"):
        if not bot_token or not signing_secret:
            st.error("Bot Token と Signing Secret が設定されていません。")
        else:
            # Boltアプリ生成
            st.session_state["app"] = App(token=bot_token, signing_secret=signing_secret)

            try:
                # チャンネル一覧の取得
                ch_list = get_all_channels(bot_token)
                # ユーザー一覧の取得
                us_list = get_all_users(bot_token)

                # チャンネルとユーザーの選択肢を作成
                channel_options = [
                    f"Channel: {ch['name']} ({ch['id']})"
                    for ch in ch_list
                ]

                user_options = []
                for user in us_list:
                    # Botや削除済みユーザーなどを除外したい場合は条件を追加
                    if user.get("deleted") or user.get("is_bot") or user.get("id") == "USLACKBOT":
                        continue
                    display_name = user.get("profile", {}).get("display_name") or user.get("name")
                    user_options.append(f"User: {display_name} ({user['id']})")

                # セッションステートに保存
                st.session_state["channel_options"] = channel_options
                st.session_state["user_options"] = user_options

                st.success("チャンネル・ユーザー一覧を更新しました。")

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
    
    # --- 2) 送信先の複数選択 ---
    if "channel_options" in st.session_state and "user_options" in st.session_state:
        all_options = st.session_state["channel_options"] + st.session_state["user_options"]
        selected_items = st.multiselect("送信先を選択してください", all_options)

        # メッセージ入力
        message_text = st.text_area("送信メッセージを入力", value="", height=100)

        # 日時の入力（日本時間として解釈）
        datetime_str = st.text_input("予約日時 (YYYY-MM-DD HH:MM, JST)", "2025-03-08 09:05")

        # --- 3) 「予約投稿する」ボタン ---
        if st.button("予約投稿する"):
            # Boltアプリが初期化されているか確認
            if "app" not in st.session_state:
                st.error("先に「チャンネル・ユーザー一覧を取得」を実行してください。")
                return

            if not selected_items:
                st.error("送信先が選択されていません。")
                return
            if not message_text:
                st.error("メッセージを入力してください。")
                return

            # 日時をパースしてUnixタイムスタンプに変換
            try:
                jst = pytz.timezone("Asia/Tokyo")
                target_time_naive = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                target_time = jst.localize(target_time_naive)
                post_at = int(target_time.timestamp())
            except ValueError:
                st.error("日時のフォーマットが正しくありません。YYYY-MM-DD HH:MM 形式で入力してください。")
                return

            # 予約投稿の実行
            success_list = []
            for item in selected_items:
                # item 例: "Channel: general (C12345678)" or "User: bob (U12345678)"
                # ID部分を抜き出す (括弧()の中のID)
                left_paren = item.rfind("(")
                right_paren = item.rfind(")")
                if left_paren == -1 or right_paren == -1:
                    st.warning(f"形式が想定外です: {item}")
                    continue

                rid = item[left_paren+1:right_paren]  # "C12345678" or "U12345678"

                # ユーザーIDの場合は DM チャネルを開く
                if rid.startswith("U"):
                    result = st.session_state["app"].client.conversations_open(users=rid)
                    channel_id = result["channel"]["id"]
                else:
                    # チャンネルIDの場合はそのまま
                    channel_id = rid

                response = st.session_state["app"].client.chat_scheduleMessage(
                    channel=channel_id,
                    text=message_text,
                    post_at=post_at
                )
                success_list.append(f"{channel_id} (scheduled_message_id: {response['scheduled_message_id']})")

            st.success("以下の送信先に予約投稿を行いました:\n" + "\n".join(success_list))

if __name__ == "__main__":
    main()
