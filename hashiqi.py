#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
哈士奇签到脚本（回车分隔Cookie版）
更新时间：2025-03-29
特点：
1. 支持回车/换行分隔的多账号Cookie
2. 保留1-30分钟随机延迟
3. 完整PushPlus通知
"""
import os
import time
import random
import requests

def load_config():
    """加载配置（支持回车分隔Cookie）"""
    config = {
        "cookies": [],
        "pushplus_token": os.getenv("PUSHPLUS_TOKEN", "").strip()
    }
    
    raw_cookies = os.getenv("HASHIQI_COOKIES", "")
    if not raw_cookies:
        print("❌ 错误：未检测到HASHIQI_COOKIES环境变量")
        print("💡 配置指南：")
        print("1. 在青龙面板添加环境变量")
        print("2. 值填写格式（直接换行不用||符号）：")
        print('''ASP.NET_SessionId=xxx;其他cookie
ASP.NET_SessionId=yyy;其他cookie''')
        return None
    
    # 支持\n和\r\n两种换行符
    cookies = [line.strip() for line in raw_cookies.splitlines() if line.strip()]
    valid_cookies = [c for c in cookies if "ASP.NET_SessionId" in c]
    
    if not valid_cookies:
        print("❌ 错误：未找到有效的Cookie格式")
        print("💡 必须包含ASP.NET_SessionId字段")
        return None
    
    config["cookies"] = valid_cookies
    return config

NOTIFICATION_TEMPLATE = """
🔔 哈士奇签到结果（账号{account_num}）
├ 状态: {status}
├ 详情: {message}
└ 时间: {time}
"""

def send_notification(title, content, token):
    """发送PushPlus通知"""
    if not token:
        return False
    try:
        requests.post(
            "http://www.pushplus.plus/send",
            json={
                "token": token,
                "title": title,
                "content": content,
                "template": "txt"
            },
            timeout=10
        )
        return True
    except:
        return False

def do_sign(session):
    """执行签到核心逻辑"""
    try:
        # 获取签到页面
        html = session.get(
            "https://vip.ioshashiqi.com/aspx3/mobile/qiandao.aspx?action=list&s=&no="
        ).text
        
        # 提取表单参数
        viewstate = html.split('id="__VIEWSTATE" value="')[1].split('"')[0]
        generator = html.split('id="__VIEWSTATEGENERATOR" value="')[1].split('"')[0]
        
        # 提交签到
        response = session.post(
            "https://vip.ioshashiqi.com/aspx3/mobile/qiandao.aspx",
            data={
                "__VIEWSTATE": viewstate,
                "__VIEWSTATEGENERATOR": generator,
                "__EVENTTARGET": "_lbtqd",
                "__EVENTARGUMENT": ""
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # 解析结果
        if 'id="lblprice"' not in response.text:
            return False, "结果解析失败"
        return True, response.text.split('id="lblprice">')[1].split("<")[0].strip()
    except Exception as e:
        return False, f"请求异常: {str(e)}"

def main():
    print("="*50)
    print("  哈士奇签到脚本（回车分隔版）")
    print("="*50)
    
    config = load_config()
    if not config:
        return
    
    for idx, cookie in enumerate(config["cookies"], 1):
        print(f"\n🔄 处理账号 {idx}/{len(config['cookies'])}")
        
        # 随机延迟
        delay = random.randint(60, 1800)
        print(f"⏳ 延迟 {delay//60}分{delay%60}秒")
        #time.sleep(delay)
        
        # 创建会话
        session = requests.Session()
        session.headers = {
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        
        # 执行签到
        success, msg = do_sign(session)
        notification = NOTIFICATION_TEMPLATE.format(
            account_num=idx,
            status="✅ 成功" if success else "❌ 失败",
            message=msg,
            time=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        print(notification)
        send_notification(
            title=f"哈士奇签到{'成功' if success else '失败'}",
            content=notification,
            token=config["pushplus_token"]
        )

if __name__ == '__main__':
    main() 
