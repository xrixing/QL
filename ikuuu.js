/*
 * ikuuu机场签到。注册：https://ikuuu.one/auth/register?code=WOIA
 * 环境变量： IKUUU，必填。格式： 邮箱#密码，也可以是 cookie（有效期一个星期）。多个账户以 & 或 \n 换行分割
 * 环节变量： SSPANEL_HOST，可选。可以指定任何基于 SSPANEL 搭建的机场用于签到
 * 示例：process.env.IKUUU=邮箱1#密码1&邮箱2#密码2
 * 或：process.env.IKUUU=cookie1&cookie2
 */
const axios = require('axios');

class Env {
  constructor(name) {
    this.name = name;
    this.storage = new Storage();
    this.logs = [];
    this.startTime = new Date();
  }

  log(msg, level = 'info') {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [${level.toUpperCase()}] ${msg}`;
    this.logs.push(logEntry);
    console[level === 'error' ? 'error' : 'log'](logEntry);
  }

  async init(fn, envName) {
    try {
      const configs = process.env[envName]?.split(/&|\n/) || [];
      for (const cfg of configs) {
        if (cfg.trim()) {
          await fn.call(this, cfg.trim());
        }
      }
    } catch (e) {
      this.log(`初始化错误: ${e.message}`, 'error');
    }
  }

  async done() {
    const endTime = new Date();
    const duration = (endTime - this.startTime) / 1000;
    this.log(`任务执行完成，耗时 ${duration} 秒`);
    
    if (process.env.PUSHPLUS_TOKEN) {
      await this.sendPushPlusNotification();
    }
  }

  async sendPushPlusNotification() {
    try {
      const title = `${this.name}签到结果`;
      const content = this.logs.join('\n');
      
      await axios.post('http://www.pushplus.plus/send', {
        token: process.env.PUSHPLUS_TOKEN,
        title,
        content,
        template: 'txt'
      });
      
      this.log('PushPlus通知发送成功');
    } catch (e) {
      this.log(`发送PushPlus通知失败: ${e.message}`, 'error');
    }
  }
}

class Storage {
  constructor() {
    this.data = {};
  }

  getItem(key) {
    return this.data[key] || {};
  }

  setItem(key, value) {
    this.data[key] = value;
  }
}

class Request {
  constructor() {
    this.instance = axios.create({
      timeout: 10000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
      }
    });
    this.headers = {};
  }

  setHeaders(headers) {
    this.headers = { ...this.headers, ...headers };
  }

  async request(method, url, data = {}, headers = {}) {
    try {
      const response = await this.instance({
        method,
        url,
        data,
        headers: { ...this.headers, ...headers }
      });
      return response.data || {};
    } catch (error) {
      if (error.response) {
        return error.response.data || {};
      }
      return { msg: error.message, error: true };
    }
  }
}

const $ = new Env('ikuuu机场签到');
$.req = new Request();

async function getIkuuuHost() {
  if (process.env.SSPANEL_HOST) return process.env.SSPANEL_HOST;
  let host = 'https://ikuuu.one';
  try {
    const { data: html } = await $.req.request('GET', 'https://ikuuu.club');
    host = /<p><a href="(https:\/\/[^"]+)\/?"/g.exec(html)?.[1] || host;
  } catch (e) {
    $.log(`获取主机地址失败: ${e.message}`, 'error');
  }
  return host.replace(/\/$/, '');
}

async function signCheckIn(cfg) {
  const [email, passwd, HOST = await getIkuuuHost()] = cfg.split('#');
  const url = {
    login: `${HOST}/auth/login`,
    checkin: `${HOST}/user/checkin`,
  };
  let cookie = passwd ? '' : email;
  const cache = $.storage.getItem(`ikuuu_cookie`) || {};
  const cacheKey = `${HOST}_${email}`;

  if (email && passwd) {
    cookie = cache[cacheKey];
    if (cookie) {
      $.log(`使用缓存 cookie: ${cookie}`);
      $.req.setHeaders({ cookie });
      if (await checkin(url.checkin, true)) return;
      cookie = '';
    }
  }

  if (!cookie && email && passwd) {
    const data = await $.req.request('POST', url.login, { email, passwd });
    if (data.ret === 1) {
      const cookieHeader = data.headers?.['set-cookie'] || [];
      cookie = cookieHeader.map(d => d.split(';')[0]).join(';');
      $.log(data.msg || `登录成功！`);
      cache[cacheKey] = cookie;
      $.storage.setItem(`ikuuu_cookie`, cache);
    } else {
      $.log(data.msg || `登录失败！`, 'error');
      return;
    }
  }

  if (cookie) {
    $.req.setHeaders({ cookie });
    await checkin(url.checkin);
  }
}

async function checkin(url, isUseCache = false) {
  $.log(`尝试签到: ${url}`);
  try {
    const data = await $.req.request('POST', url);
    if (data.ret === 1 || String(data.msg || '').includes('签到过')) {
      $.log(`签到成功！${data.msg}`);
      return true;
    } else {
      $.log(`❌签到失败：${data.msg || '未知错误'}`, isUseCache ? 'info' : 'error');
    }
  } catch (e) {
    $.log(`签到请求异常: ${e.message}`, 'error');
  }
  return false;
}

// 独立运行
(async () => {
  try {
    await $.init(signCheckIn, 'IKUUU');
    await $.done();
  } catch (e) {
    $.log(`运行出错: ${e.message}`, 'error');
    await $.done();
    process.exit(1);
  }
})();
