import streamlit as st
from slack_bolt import App
import requests
import pytz
from datetime import datetime

def get_all_channels(bot_token):
    ...

def get_all_users(bot_token):
    ...

def main():
    st.title("Slack 予約投稿アプリ（Streamlit版）")

    # --- Secrets からトークン取得 ---
    #   Streamlit Cloud の [Secrets] タブで設定するか、
    #   ローカルの場合は .streamlit/secrets.toml を使う
    bot_token = st.secrets["SLACK_BOT_TOKEN"]
    signing_secret = st.secrets["SLACK_SIGNING_SECRET"]

    if st.button("チャンネル・ユーザー一覧を取得"):
        if not bot_token or not signing_secret:
            st.error("Bot Token と Signing Secret を設定してください。")
        else:
            st.session_state["app"] = App(token=bot_token, signing_secret=signing_secret)

            try:
                ch_list = get_all_channels(bot_token)
                us_list = get_all_users(bot_token)

                channel_options = [
                    f"Channel: {ch['name']} ({ch['id']})"
                    for ch in ch_list
                ]

                user_options = []
                for user in us_list:
                    if user.get("deleted") or user.get("is_bot") or user.get("id") == "USLACKBOT":
                        continue
                    display_name = user.get("profile", {}).get("display_name") or user.get("name")
                    user_options.append(f"User: {display_name} ({user['id']})")

                st.session_state["channel_options"] = channel_options
                st.session_state["user_options"] = user_options

                st.success("チャンネル・ユーザー一覧を更新しました。")

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

    if "channel_options" in st.session_state and "user_options" in st.session_state:
        ...
        # 以下はColabのときと同じロジック
        # 予約投稿の実行など
        ...

if __name__ == "__main__":
    main()
