import os
import re
import requests
import time
from urllib.parse import unquote
from datetime import datetime

def get_env(name):
    value = os.getenv(name)
    if not value:
        raise ValueError(f"环境变量 {name} 未配置")
    return value

def validate_cookies(cookie_str):
    required_keys = {
        'rHEX_2132_saltkey',
        'rHEX_2132_auth',
        'rHEX_2132_client_token',
        'waf_captcha_marker'
    }
    cookies = {}
    for item in cookie_str.strip().split(';'):
        if '=' in item:
            name, value = item.split('=', 1)
            cookies[name.strip()] = unquote(value.strip())
    missing = required_keys - cookies.keys()
    if missing:
        raise ValueError(f"缺少必要Cookie字段：{', '.join(missing)}")
    return cookies

def create_session(cookies):
    session = requests.Session()
    session.headers.update({
        'authority': 'www.right.com.cn',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'zh-CN,zh;q=0.9',
        'referer': 'https://www.right.com.cn/FORUM/',
        'sec-ch-ua': '"Microsoft Edge";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.60',
    })
    
    cookies['rHEX_2132_lastact'] = f"{int(time.time())}%09home.php%09space"
    session.cookies.update(cookies)
    
    waf_check = session.get('https://www.right.com.cn/FORUM/forum.php', timeout=10)
    if 'waf_verifying' in waf_check.text:
        raise RuntimeError("触发WAF验证，请更新Cookie")
    return session

def extract_credits(html):
    credit_patterns = [
        r'id="extcreditmenu"[^>]*>积分: (\d+)',
        r'积分:\s*</em>\s*(\d+)',
        r'积分: <strong>(\d+)</strong>',
        r'积分: (\d+)'
    ]
    for pattern in credit_patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    with open('debug_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    raise ValueError("积分解析失败，已保存调试页面")

def format_notification(status, credits):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
🔔 恩山论坛签到结果（账号1）

├ 状态: {status}
├ 奖励: {credits} 积分
└ 时间: {current_time}
""".strip()

def push_notification(content):
    token = os.getenv('PUSHPLUS_TOKEN')
    if not token:
        return
    
    try:
        requests.post(
            'http://www.pushplus.plus/send',
            json={
                "token": token,
                "title": "🔔 恩山论坛签到通知",
                "content": content,
                "template": "markdown"
            },
            timeout=10
        )
    except Exception as e:
        print(f"推送失败：{str(e)}")

def main():
    try:
        cookie_str = get_env('ENSHAN_COOKIE')
        cookies = validate_cookies(cookie_str)
        
        session = create_session(cookies)
        
        actions = [
            ('get', 'forum.php'),
            ('get', 'home.php?mod=spacecp'),
            ('get', 'home.php?mod=space&do=notice')
        ]
        
        for method, path in actions:
            url = f'https://www.right.com.cn/FORUM/{path}'
            res = getattr(session, method)(url, timeout=15)
            res.raise_for_status()
            time.sleep(1)
        
        profile_res = session.get('https://www.right.com.cn/FORUM/home.php?mod=spacecp', timeout=15)
        credits = extract_credits(profile_res.text)
        
        # 构建通知内容
        notification = format_notification("✅ 成功", credits)
        push_notification(notification)
        return notification
        
    except requests.exceptions.RequestException as e:
        error_msg = format_notification("❌ 失败", 0).replace("✅", "❌")
    except ValueError as e:
        error_msg = format_notification(f"❌ 数据异常（{str(e)}）", 0)
    except Exception as e:
        error_msg = format_notification(f"❌ 系统错误（{str(e)}）", 0)
    
    push_notification(error_msg)
    return error_msg

if __name__ == "__main__":
    print(main())
