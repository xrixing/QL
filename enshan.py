#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import os
import sys
import urllib.parse
import requests
from bs4 import BeautifulSoup
import time
import random

def log_message(message, error=False):
    if error:
        print(f"ERROR: {message}")
    else:
        print(f"INFO: {message}")

def send_pushplus_message(title, content):
    """发送 Pushplus 消息"""
    pushplus_token = os.getenv('PUSHPLUS_TOKEN')
    if not pushplus_token:
        log_message("Pushplus token 未设置", error=True)
        return
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": pushplus_token,
        "title": title,
        "content": content
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        log_message("Pushplus 消息发送成功")
    else:
        log_message("Pushplus 消息发送失败", error=True)

def user_data(cookie):
    """获取用户信息"""
    url = 'https://www.right.com.cn/FORUM/home.php?mod=spacecp&ac=credit&op=base'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.62',
        'Referer': 'https://www.right.com.cn/FORUM/home.php?mod=spacecp&ac=credit&showcredit=1',
        'Cookie': cookie
    }
    response = requests.get(url, headers=headers)
    status_code = response.status_code
    if status_code == 200:
        soup = BeautifulSoup(response.content.decode('utf-8'), "html.parser")
        user_name = soup.find('a', attrs={'title': '访问我的空间'}).text  # 用户名
        points = soup.find('a', attrs={'id': 'extcreditmenu'}).text  # 目前积分
        user_group = soup.find('a', attrs={'id': 'g_upmine'}).text  # 用户组
        log_message(f"模拟登录成功---{user_name}---{points}---{user_group}")
        return f"模拟登录成功---{user_name}---{points}---{user_group}"
    else:
        log_message(f"账号可能cookie过期了", error=True)
        return "账号可能cookie过期了"

def sign_in(number, cookie):
    """开启模拟登录"""
    cookie = urllib.parse.unquote(cookie)
    cookie_list = cookie.split(";")
    parsed_cookie = ''
    for i in cookie_list:
        parts = i.split("=", 1)
        key = parts[0].strip()
        if key == "rHEX_2132_saltkey":
            parsed_cookie += f"rHEX_2132_saltkey={urllib.parse.quote(parts[1])}; "
        if key == "rHEX_2132_auth":
            parsed_cookie += f"rHEX_2132_auth={urllib.parse.quote(parts[1])}; "
    if not ('rHEX_2132_saltkey' in parsed_cookie and 'rHEX_2132_auth' in parsed_cookie):
        log_message(f"第{number}cookie中未包含rHEX_2132_saltkey或rHEX_2132_auth字段，请检查cookie", error=True)
        sys.exit()
    
    url = "https://www.right.com.cn/forum/home.php?mod=spacecp&ac=credit&op=log&suboperation=creditrulelog"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Cookie": parsed_cookie,
        "Host": "www.right.com.cn",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.200",
        "sec-ch-ua": "\"Not/A)Brand\";v=\"99\", \"Microsoft Edge\";v=\"115\", \"Chromium\";v=\"115\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }
    
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        trs = soup.find("table", summary="积分获得历史").find_all("tr")
        for tr in trs:
            tds = tr.find_all("td")
            if len(tds) == 0:
                continue
            if tds[0].text == "每天登录" and tds[5].text[:10] == datetime.datetime.now().strftime("%Y-%m-%d"):
                log_message("模拟登录成功")
                user_info = user_data(parsed_cookie)  # 获取用户信息
                return f"账号 {number} 模拟登录成功: {user_info}"
        else:
            log_message("模拟登录失败", error=True)
            return f"账号 {number} 模拟登录失败"
    else:
        log_message("账号可能cookie过期", error=True)
        return f"账号 {number} 账号可能cookie过期"

def main():
    """主方法，开始模拟登录"""
    log_message("开始获取Cookie\n")

    # 增加随机等待时间（0到10分钟）
    wait_time = random.randint(0, 10 * 60)
    log_message(f"随机等待时间：{wait_time // 60} 分钟 {wait_time % 60} 秒")
    time.sleep(wait_time)
    
    if os.environ.get("ENSHAN_COOKIE"):
        cookies = os.environ.get("ENSHAN_COOKIE")
    else:
        log_message("请在环境变量填写ENSHAN_COOKIE的值", error=True)
        sys.exit()  # 未获取到cookie，退出系统
    
    for number, cookie in enumerate(cookies.split("&")):
        log_message(f"开始执行第{number + 1}个账号")
        result_message = sign_in(number + 1, cookie)  # 模拟登录
        send_pushplus_message("恩山论坛签到结果", result_message)

if __name__ == '__main__':
    main()  # 主方法
    log_message("恩山论坛登录任务已完成")
