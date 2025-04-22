#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云盘签到推送版
更新时间：2024-06-20
环境变量：
ALIYUN_TOKENS   : 多个refresh_token用换行分隔
PUSHPLUS_TOKEN  : 推送Token（可选）
"""
import os
import time
import uuid
import hashlib
import requests
from datetime import datetime

class AliYunSigner:
    def __init__(self, refresh_token):
        self.refresh_token = refresh_token
        self.session = requests.Session()
        self.device_id = "6dfa3b2c9d4e7f01"
        self._setup_headers()

    def _setup_headers(self):
        self.session.headers = {
            "User-Agent": "AliApp(AYSD/5.8.1) com.alicloud.databox/40603030",
            "X-Device-Id": self.device_id,
            "X-Request-Id": str(uuid.uuid4()),
            "Content-Type": "application/json"
        }

    def _generate_signature(self):
        timestamp = int(time.time() * 1000)
        raw_str = f"{self.device_id}||{timestamp}||5.8.1||40603030"
        return hashlib.md5(raw_str.encode()).hexdigest().upper()

    def login(self):
        try:
            resp = self.session.post(
                "https://auth.aliyundrive.com/v2/account/token",
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "_signature": self._generate_signature()
                },
                timeout=10
            )
            data = resp.json()
            if "access_token" not in data:
                return False, data.get("message", "未知错误")
            self.session.headers["Authorization"] = f"Bearer {data['access_token']}"
            return True, "登录成功"
        except Exception as e:
            return False, f"登录异常：{str(e)}"

    def _get_sign_days(self):
        try:
            resp = self.session.post(
                "https://member.aliyundrive.com/v2/activity/sign_in_list",
                json={"_rx-s": "mobile", "deviceId": self.device_id},
                timeout=10
            )
            return resp.json().get("result", {}).get("signInCount", 0)
        except:
            return 0

    def process_sign(self):
        result = {
            "status": "",
            "days": 0,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "account": ""
        }

        # 登录流程
        login_success, login_msg = self.login()
        if not login_success:
            result["status"] = f"❌ 登录失败（{login_msg[:10]}）"
            return result

        # 签到流程
        try:
            original_days = self._get_sign_days()
            sign_resp = self.session.post(
                "https://member.aliyundrive.com/v1/activity/sign_in",
                json={"_rx-s": "mobile"},
                timeout=10
            )
            
            if sign_resp.json().get("success"):
                updated_days = self._get_sign_days()
                result["days"] = updated_days
                result["status"] = "✅ 签到成功" if updated_days > original_days else "⚠️ 重复签到"
            else:
                result["status"] = "⚠️ 签到失败"
                result["days"] = original_days
                
        except Exception as e:
            result["status"] = f"❌ 系统异常（{str(e)[:10]}）"
        
        return result

def push_notification(token, content):
    """发送PUSHPLUS通知"""
    url = "https://www.pushplus.plus/send"
    payload = {
        "token": token,
        "title": "🔔 阿里云签到结果",
        "content": content,
        "template": "txt"
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.json().get("code") == 200
    except:
        return False

def main():
    tokens = [t.strip() for t in os.getenv("ALIYUN_TOKENS", "").splitlines() if t.strip()]
    pushplus_token = os.getenv("PUSHPLUS_TOKEN")
    
    if not tokens:
        print("❌ 请设置环境变量 ALIYUN_TOKENS")
        return

    print("="*40)
    print(f"  阿里云盘自动签到  {datetime.now().strftime('%Y-%m-%d')}")
    print("="*40)

    results = []
    for index, token in enumerate(tokens, 1):
        print(f"\n🔄 处理账号 {index}/{len(tokens)}")
        signer = AliYunSigner(token)
        result = signer.process_sign()
        result["account"] = f"账号{index}"
        
        # 控制台输出
        output = f"""
🔔 阿里云签到结果（{result['account']}）
├ 状态: {result['status']}
├ 累计: {result['days']}天
└ 时间: {result['time']}
""".strip()
        print(output)
        results.append(result)

    # 发送推送通知
    if pushplus_token and results:
        content = ""
        for res in results:
            content += f"""
🔔 阿里云签到结果（{res['account']}）
├ 状态: {res['status']}
├ 累计: {res['days']}天
└ 时间: {res['time']}
"""
        success = push_notification(pushplus_token, content.strip())
        print(f"\n📤 推送通知状态: {'成功' if success else '失败'}")

    print("\n🏁 所有账号处理完成")

if __name__ == '__main__':
    start_time = datetime.now()
    main()
    duration = (datetime.now() - start_time).total_seconds()
    print(f"\n## 执行结束 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  耗时 {duration:.2f} 秒")
