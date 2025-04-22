#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
塔斯汀汉堡签到脚本（2024-05-20更新版）
更新时间：2024-05-20
特点：
1. 使用最新验证有效的活动ID(58)
2. 优化请求成功率
3. 增强错误处理
"""
import os
import random
import time
import requests
from datetime import datetime

# ============================================
#                 配置区域
# ============================================
NOTIFICATION_TEMPLATE = """
🔔 塔斯汀签到结果（账号{account_num}）
├ 状态: {status}
├ 奖励: {reward}
└ 时间: {time}
"""

BASE_CONFIG = {
    "version": "1.46.8",
    "base_url": "https://sss-web.tastientech.com",
    "channel": "1",
    "activity_id": "58"  # 从抓包数据确认的最新有效ID
}

# ============================================
#                 核心功能
# ============================================
class TastienSigner:
    def __init__(self, cookie):
        self.cookie = cookie
        self.headers = {
            'user-token': cookie,
            'version': BASE_CONFIG["version"],
            'channel': BASE_CONFIG["channel"]
        }
    
    def random_delay(self):
        """随机延迟1-30分钟"""
        delay = random.randint(60, 1800)
        print(f"⏳ 延迟 {delay//60}分{delay%60}秒")
        time.sleep(delay)
    
    def get_activity_id(self):
        """直接使用已验证的有效活动ID"""
        return BASE_CONFIG["activity_id"]
    
    def get_member_info(self):
        """获取会员信息（增强重试机制）"""
        url = f"{BASE_CONFIG['base_url']}/api/intelligence/member/getMemberDetail"
        for _ in range(3):  # 增加重试机制
            try:
                resp = requests.get(url, headers=self.headers, timeout=15).json()
                if resp.get('code') == 200:
                    return resp['result']['phone']
                time.sleep(2)  # 失败后等待2秒重试
            except Exception as e:
                print(f"❌ 获取会员信息失败: {str(e)}")
        return None
    
    def do_sign(self):
        """执行签到（优化请求参数）"""
        activity_id = self.get_activity_id()
        print(f"[DEBUG] 使用活动ID: {activity_id}")  # 调试信息
        
        phone = self.get_member_info()
        if not phone:
            return False, "获取用户信息失败"
        
        url = f"{BASE_CONFIG['base_url']}/api/sign/member/signV2"
        data = {
            "activityId": activity_id,
            "memberName": "",
            "memberPhone": phone,
            "shopId": ""  # 新增必要参数
        }
        
        try:
            resp = requests.post(url, headers=self.headers, json=data, timeout=15).json()
            if resp.get('code') == 200:
                reward = resp['result']['rewardInfoList'][0]
                return True, f"{reward.get('rewardName', '积分')}x{reward.get('num', 1)}"
            return False, resp.get('msg', '未知错误')
        except Exception as e:
            return False, f"请求异常: {str(e)}"

# ============================================
#                 辅助功能
# ============================================
def load_config():
    """加载环境变量配置"""
    return {
        "cookies": [c for c in os.getenv("TASTIEN_COOKIES", "").splitlines() if c.strip()],
        "pushplus_token": os.getenv("PUSHPLUS_TOKEN", "").strip()
    }

def send_notification(content, token):
    """发送通知（优化失败重传）"""
    if not token:
        return False
    
    for _ in range(3):  # 最多重试3次
        try:
            resp = requests.post(
                "http://www.pushplus.plus/send",
                json={
                    "token": token,
                    "title": "塔斯汀签到报告",
                    "content": content,
                    "template": "txt"
                },
                timeout=10
            )
            if resp.status_code == 200:
                return True
        except:
            time.sleep(2)
    return False

# ============================================
#                 主程序
# ============================================
def main():
    print("="*40)
    print("塔斯汀自动签到 v2.1")
    print("="*40)
    
    config = load_config()
    if not config["cookies"]:
        print("❌ 未检测到有效的TASTIEN_COOKIES环境变量")
        print("配置指南：")
        print("1. 在环境变量中添加TASTIEN_COOKIES")
        print("2. 值格式：每行一个user-token")
        return
    
    results = []
    for idx, cookie in enumerate(config["cookies"], 1):
        print(f"\n🔍 处理第 {idx} 个账号")
        
        signer = TastienSigner(cookie.strip())
        signer.random_delay()
        
        success, msg = signer.do_sign()
        status = "✅ 成功" if success else "❌ 失败"
        
        result = NOTIFICATION_TEMPLATE.format(
            account_num=idx,
            status=status,
            reward=msg,
            time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        results.append(result)
        print(result)
    
    if config["pushplus_token"]:
        send_notification("\n".join(results), config["pushplus_token"])

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        print(f"💥 致命错误: {str(e)}")
