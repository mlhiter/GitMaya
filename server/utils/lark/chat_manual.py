from .base import *


class ChatManual(FeishuMessageCard):
    def __init__(
        self,
        repo_url="https://github.com/ConnectAI-E/GitMaya",
        actions=[],
        repo_name="GitMaya",
    ):
        github_url = "https://github.com"
        elements = [
            GitMayaTitle(),
            FeishuMessageHr(),
            FeishuMessageDiv(
                content="**📄 创建 Issue **\n*群聊下回复「/issue + 新 Issue 标题 + @分配成员」 *\n*群聊绑定多仓库时，请在对应仓库话题下创建 Issue *",
                tag="lark_md",
            ),
            # FeishuMessageDiv(
            #     content="**🚀 运行 Action **\n*群聊下回复「/action」 *",
            #     tag="lark_md",
            #     extra=FeishuMessageSelect(
            #         *[FeishuMessageOption(value=action) for action in actions],
            #         placeholder="选择想要执行的 Action",
            #         value={
            #             "key": "value",  # TODO
            #         },
            #     )
            #     if len(actions) > 0
            #     else None,
            # ),
            FeishuMessageDiv(
                content="**🗄 关联新仓库至当前群聊 **\n*群聊下回复「/match + repo url」或「/match --replace + repo url」*",
                tag="lark_md",
            ),
            FeishuMessageDiv(
                content="**🧹 解绑当前群仓库 **\n*群聊下回复「/unmatch」 *",
                tag="lark_md",
            ),
            FeishuMessageDiv(
                content=f"**⚡️ 前往 GitHub 查看 Repo 主页 **\n*群聊下回复「/view」 *",
                tag="lark_md",
                extra=FeishuMessageButton(
                    "打开 GitHub 主页",
                    tag="lark_md",
                    type="default",
                    multi_url={
                        "url": repo_url,
                        "android_url": repo_url,
                        "ios_url": repo_url,
                        "pc_url": repo_url,
                    },
                ),
            ),
            FeishuMessageDiv(
                content=f"**📈 前往 GitHub 查看 Repo Insight **\n*群聊下回复「/insight」 *",
                tag="lark_md",
                extra=FeishuMessageButton(
                    "打开 Insight 面板",
                    tag="lark_md",
                    type="default",
                    multi_url={
                        "url": f"{repo_url}/pulse",
                        "android_url": f"{repo_url}/pulse",
                        "ios_url": f"{repo_url}/pulse",
                        "pc_url": f"{repo_url}/pulse",
                    },
                ),
            ),
            GitMayaCardNote("GitMaya Chat Manual"),
        ]
        header = FeishuMessageCardHeader("GitMaya Chat Manual\n", template="grey")
        config = FeishuMessageCardConfig()

        super().__init__(*elements, header=header, config=config)


class ChatView(FeishuMessageCard):
    def __init__(
        self,
        repo_url="https://github.com/ConnectAI-E/GitMaya",
    ):
        elements = [
            FeishuMessageDiv(
                content=f"** ⚡️ 前往 GitHub 查看信息 **",
                tag="lark_md",
                extra=FeishuMessageButton(
                    "在浏览器打开",
                    tag="lark_md",
                    type="default",
                    multi_url={
                        "url": repo_url,
                        "android_url": repo_url,
                        "ios_url": repo_url,
                        "pc_url": repo_url,
                    },
                ),
            ),
            GitMayaCardNote("GitMaya Chat Action"),
        ]
        header = FeishuMessageCardHeader("🎉 操作成功！")
        config = FeishuMessageCardConfig()

        super().__init__(*elements, header=header, config=config)


if __name__ == "__main__":
    import json
    import os

    import httpx
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv())
    message = ChatManual(actions=["aaa", "bbb"])
    print(json.dumps(message))
    result = httpx.post(
        os.environ.get("TEST_BOT_HOOK"),
        json={"card": message, "msg_type": "interactive"},
    ).json()
    print(result)
