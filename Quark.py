#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import os
import re
import sys
import time
import random
import requests

# 日志信息函数
def log_message(message, error=False):
    """打印日志信息"""
    if error:
        print(f"❌ {message}")
    else:
        print(f"✅ {message}")

# 简化消息通知函数
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

# 获取环境变量
def get_env():
    if "QUARK_COOKIE" in os.environ:
        cookie_list = re.split('\n|&&', os.environ.get('QUARK_COOKIE'))
    else:
        print('❌ 未添加 QUARK_COOKIE 变量')
        send_pushplus_message('夸克自动签到', '❌ 未添加 QUARK_COOKIE 变量')
        sys.exit(0)
    return cookie_list

class Quark:
    def __init__(self, user_data, account_index):
        self.param = user_data
        self.account_index = account_index

    def convert_bytes(self, b):
        units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = 0
        while b >= 4 and i < len(units) - 1:
            b /= 1024
            i += 1
        return f"{b:.2f} {units[i]}"

    def get_growth_info(self):
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
        querystring = {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.param.get('kps'),
            "sign": self.param.get('sign'),
            "vcode": self.param.get('vcode')
        }
        response = requests.get(url=url, params=querystring).json()
        if response.get("data"):
            log_message("获取成长信息成功")
            return response["data"]
        else:
            log_message("获取成长信息失败", error=True)
            return False

    def get_growth_sign(self):
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign"
        querystring = {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.param.get('kps'),
            "sign": self.param.get('sign'),
            "vcode": self.param.get('vcode')
        }
        data = {"sign_cyclic": True}
        response = requests.post(url=url, json=data, params=querystring).json()
        if response.get("data"):
            log_message("签到成功")
            return True, response["data"]["sign_daily_reward"]
        else:
            log_message(f"签到失败: {response['message']}", error=True)
            return False, response["message"]

    def do_sign(self):
        log = ""
        growth_info = self.get_growth_info()
        if growth_info:
            sign_status, sign_reward = self.get_growth_sign()
            log += (
                f"账号 {self.account_index + 1}:\n"
                f"- 用户类型: {'88VIP' if growth_info['88VIP'] else '普通用户'}\n"
                f"- 网盘总容量: {self.convert_bytes(growth_info['total_capacity'])}\n"
                f"- 已用容量: {self.convert_bytes(growth_info['use_capacity'])}\n"
                f"- 今日已签到: {'是' if growth_info['cap_sign']['sign_daily'] else '否'}\n"
                f"- 连续签到天数: {growth_info['cap_sign']['sign_progress']}/{growth_info['cap_sign']['sign_target']}\n"
                f"- 今日签到奖励: {self.convert_bytes(sign_reward) if sign_status else 'N/A'}\n"
                f"- 累计签到奖励: {self.convert_bytes(growth_info['cap_composition']['sign_reward'])}\n"
                f"- 今日签到账户容量: {self.convert_bytes(growth_info['cap_composition'].get('other', 0))}\n\n"
            )
            print(log)  # 打印详细信息到日志
        else:
            log += f"账号 {self.account_index + 1}:\n❌ 获取成长信息失败\n"
            print(log)  # 打印失败信息到日志
        return log

def main():
    # 添加随机延迟
    delay = random.randint(0, 1800)  # 生成一个0到1800秒（30分钟）之间的随机延迟
    print(f"延迟 {delay} 秒后开始执行任务")
    #time.sleep(delay)
    
    msg = ""
    global cookie_quark
    cookie_quark = get_env()

    print("✅ 检测到共", len(cookie_quark), "个夸克账号\n")

    for i in range(len(cookie_quark)):
        user_data = {}
        for a in cookie_quark[i].replace(" ", "").split(';'):
            if '=' in a:
                user_data.update({a.split('=')[0]: a.split('=')[1]})
            else:
                print(f"Warning: Skipping invalid variable '{a}'")
        log = Quark(user_data, i).do_sign()
        msg += log

    try:
        send_pushplus_message('夸克自动签到', msg)
    except Exception as err:
        print('%s\n❌ 错误，请查看运行日志！' % err)

    return msg

if __name__ == "__main__":
    print("----------夸克网盘开始签到----------")
    main()
    print("----------夸克网盘签到完毕----------")
