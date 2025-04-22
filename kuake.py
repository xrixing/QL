#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
夸克签到美化版（带结构化输出）
更新时间：2024-03-30
"""
import os
import time
import requests
import logging
from typing import Optional, Dict, Any

class QuarkSigner:
    def __init__(self):
        self.cookie = self.get_cookie()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Cookie": self.cookie,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        self.pushplus_token = os.getenv("PUSHPLUS_TOKEN", "")

    def get_cookie(self) -> str:
        """获取环境变量中的Cookie"""
        cookie = os.getenv("QUARK_COOKIE", "")
        if not cookie:
            self.pretty_print("❌ 未找到QUARK_COOKIE环境变量", is_error=True)
            exit()
        return cookie

    def pretty_print(self, message: str, is_error: bool = False):
        """美化控制台输出"""
        if is_error:
            logging.error(message)
        else:
            logging.info(message)

    def format_result(self, status: str, reward: str, nickname: str = "") -> str:
        """生成格式化的结果字符串"""
        lines = [
            "="*40,
            "🔔 夸克签到结果",
            f"├ 账号: {nickname}" if nickname else "",
            f"├ 状态: {status}",
            f"├ 奖励: {reward}",
            f"└ 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "="*40
        ]
        return "\n".join(filter(None, lines))

    def push_notification(self, title: str, content: str) -> bool:
        """发送结构化通知"""
        if not self.pushplus_token:
            return False
        try:
            requests.post(
                "http://www.pushplus.plus/send",
                json={
                    "token": self.pushplus_token,
                    "title": title,
                    "content": content.replace('├', '│').replace('└', '╰'),
                    "template": "txt"
                },
                timeout=10
            )
            return True
        except Exception as e:
            self.pretty_print(f"⚠️ 通知发送失败: {str(e)}", is_error=True)
            return False

    def check_login(self) -> Optional[Dict[str, Any]]:
        """检查登录状态"""
        url = "https://pan.quark.cn/account/info"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return response.json()
            self.pretty_print(f"登录验证失败，状态码: {response.status_code}", is_error=True)
            return None
        except Exception as e:
            self.pretty_print(f"登录验证异常: {str(e)}", is_error=True)
            return None

    def get_sign_status(self) -> Optional[Dict[str, Any]]:
        """获取签到状态"""
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info?pr=ucpro&fr=pc"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.pretty_print(f"获取签到状态失败: {str(e)}", is_error=True)
            return None

    def do_sign(self) -> Dict[str, Any]:
        """执行签到"""
        # 1. 验证登录状态
        account_info = self.check_login()
        if not account_info:
            return {"status": -1, "message": "登录验证失败"}

        nickname = account_info.get("data", {}).get("nickname", "未知用户")

        # 2. 检查签到状态
        sign_status = self.get_sign_status()
        if not sign_status:
            return {"status": -1, "message": "获取签到状态失败", "nickname": nickname}

        cap_sign = sign_status.get("data", {}).get("cap_sign", {})
        if cap_sign.get("sign_daily", False):
            reward = cap_sign.get("sign_daily_reward", 0)
            mb = reward // (1024 * 1024)  # 转换为MB并取整
            return {
                "status": 200, 
                "message": "今日已签到", 
                "reward": f"+{mb}MB空间",
                "nickname": nickname
            }

        # 3. 执行签到
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign?pr=ucpro&fr=pc"
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json={"sign_cyclic": True},
                timeout=15
            )
            data = response.json()

            if response.status_code == 200:
                reward = data.get("data", {}).get("sign_daily_reward", 0)
                mb = reward // (1024 * 1024) if reward else 0
                return {
                    "status": 200, 
                    "message": "签到成功", 
                    "reward": f"+{mb}MB空间",
                    "nickname": nickname
                }
            return {
                "status": -1, 
                "message": data.get("message", "签到失败"),
                "nickname": nickname
            }
        except Exception as e:
            return {
                "status": -1, 
                "message": str(e),
                "nickname": nickname
            }

if __name__ == '__main__':
    # 初始化日志格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[logging.StreamHandler()]
    )

    signer = QuarkSigner()
    result = signer.do_sign()

    # 构建输出内容
    status_icon = "✅" if result["status"] == 200 else "❌"
    output = signer.format_result(
        status=f"{status_icon} {result['message']}",
        reward=result.get("reward", "无奖励信息"),
        nickname=result.get("nickname", "")
    )

    # 输出到控制台和推送
    signer.pretty_print(output)
    if result["status"] == 200:
        signer.push_notification("夸克签到成功", output)
    else:
        signer.push_notification("夸克签到失败", output + "\n🔧 建议检查Cookie有效性") 
