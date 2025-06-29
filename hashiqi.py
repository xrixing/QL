#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
哈士奇签到脚本（无延迟快速版）
更新时间：2024-03-29
特点：
1. 去除所有延迟，快速执行
2. 优化结果解析逻辑
3. 增强错误处理
"""
import os
import time
import requests

def load_config():
    """加载配置"""
    config = {
        "cookies": [],
        "pushplus_token": os.getenv("PUSHPLUS_TOKEN", "").strip()
    }
    
    raw_cookies = os.getenv("HASHIQI_COOKIES", "")
    if not raw_cookies:
        print("❌ 错误：未检测到HASHIQI_COOKIES环境变量")
        return None
    
    config["cookies"] = [c.strip() for c in raw_cookies.splitlines() if c.strip() and "ASP.NET_SessionId" in c]
    
    if not config["cookies"]:
        print("❌ 错误：没有有效的Cookie")
        return None
    
    return config

def send_notification(title, content, token):
    """发送通知"""
    if not token:
        return False
    
    try:
        resp = requests.post(
            "http://www.pushplus.plus/send",
            json={
                "token": token,
                "title": title,
                "content": content,
                "template": "txt"
            },
            timeout=10
        )
        return resp.status_code == 200
    except:
        return False

def create_session(cookie):
    """创建请求会话"""
    session = requests.Session()
    session.headers.update({
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "Referer": "https://vip.ioshashiqi.com/aspx3/mobile/qiandao.aspx"
    })
    return session

def do_sign(session):
    """执行签到"""
    try:
        # 获取签到页面
        list_url = "https://vip.ioshashiqi.com/aspx3/mobile/qiandao.aspx?action=list"
        response = session.get(list_url, timeout=15)
        
        # 检查是否需要登录
        if "login.aspx" in response.text.lower():
            return False, "Cookie已失效"
        
        # 尝试解析表单
        viewstate = response.text.split('id="__VIEWSTATE" value="')[1].split('"')[0] if '__VIEWSTATE' in response.text else ""
        generator = response.text.split('id="__VIEWSTATEGENERATOR" value="')[1].split('"')[0] if '__VIEWSTATEGENERATOR' in response.text else ""
        
        if not viewstate:
            return False, "无法获取表单参数"
        
        # 提交签到
        post_data = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": generator,
            "__EVENTTARGET": "_lbtqd",
            "__EVENTARGUMENT": ""
        }
        
        sign_response = session.post(
            "https://vip.ioshashiqi.com/aspx3/mobile/qiandao.aspx",
            data=post_data,
            timeout=20
        )
        
        # 解析结果（新增多种匹配方式）
        if 'id="lblprice"' in sign_response.text:
            result = sign_response.text.split('id="lblprice">')[1].split("<")[0].strip()
            return True, result
        elif "今天已签到" in sign_response.text:
            return True, "今日已签到"
        elif "签到成功" in sign_response.text:
            return True, "签到成功"
        else:
            return False, "无法解析签到结果"
            
    except Exception as e:
        return False, f"请求异常: {str(e)}"

def main():
    print("="*50)
    print("  哈士奇签到脚本（快速版）")
    print(f"  开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    config = load_config()
    if not config:
        return
    
    results = []
    for idx, cookie in enumerate(config["cookies"], 1):
        print(f"\n🔄 处理账号 {idx}/{len(config['cookies'])}")
        
        try:
            session = create_session(cookie)
            success, msg = do_sign(session)
            
            result = {
                "account": idx,
                "status": "成功" if success else "失败",
                "message": msg
            }
            results.append(result)
            
            print(f"✔️ 结果: {result['status']} - {msg}")
            
            # 发送单个账号通知
            if config["pushplus_token"]:
                notification = f"""
哈士奇签到结果（账号{idx}）
状态: {'✅ 成功' if success else '❌ 失败'}
详情: {msg}
时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
                """
                send_notification(
                    title=f"哈士奇签到{'成功' if success else '失败'}",
                    content=notification,
                    token=config["pushplus_token"]
                )
                
        except Exception as e:
            print(f"❌ 发生异常: {str(e)}")
            results.append({
                "account": idx,
                "status": "异常",
                "message": str(e)
            })
    
    # 发送汇总通知
    if config["pushplus_token"] and results:
        summary = "\n".join([
            f"账号{r['account']}: {r['status']} - {r['message']}" 
            for r in results
        ])
        send_notification(
            title=f"哈士奇签到汇总（{len([r for r in results if r['status']=='成功'])}/{len(results)}成功）",
            content=summary,
            token=config["pushplus_token"]
        )

if __name__ == '__main__':
    start_time = time.time()
    main()
    print(f"\n🕒 总耗时: {time.time() - start_time:.2f}秒")
