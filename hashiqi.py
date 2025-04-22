const axios = require('axios');
const cheerio = require('cheerio');
require('dotenv').config(); // 加载环境变量

// 确认环境变量是否已正确读取
if (!process.env.HASHIQI_TOKENS || !process.env.HASHIQI_TOKENS_2 || !process.env.PUSHPLUS_TOKEN) {
    console.error('必要的环境变量未设置');
    process.exit(1);
}

// 从环境变量中读取 cookies 和 Pushplus token
const tokens = [process.env.HASHIQI_TOKENS, process.env.HASHIQI_TOKENS_2];
const pushplusToken = process.env.PUSHPLUS_TOKEN;

// 配置你的签到网址
const signInUrl = 'https://vip.ioshashiqi.com/aspx3/mobile/qiandao.aspx?action=list&s=&no=';

// 发送 Pushplus 消息
async function sendPushplusMessage(title, content) {
    const pushplusUrl = 'http://www.pushplus.plus/send';
    try {
        await axios.post(pushplusUrl, {
            token: pushplusToken,
            title: title,
            content: content
        });
    } catch (error) {
        console.error('发送 Pushplus 消息失败：', error.message);
    }
}

(async () => {
    for (let i = 0; i < tokens.length; i++) {
        const token = tokens[i].trim();
        try {
            // 获取签到页面的隐藏字段
            const response = await axios.get(signInUrl, {
                headers: {
                    Cookie: token
                }
            });

            const $ = cheerio.load(response.data);
            const viewState = $('#__VIEWSTATE').val();
            const viewStateGenerator = $('#__VIEWSTATEGENERATOR').val();

            // 模拟 __doPostBack 方法的调用
            const eventTarget = '_lbtqd';
            const eventArgument = '';

            const postData = `__VIEWSTATE=${encodeURIComponent(viewState)}&__VIEWSTATEGENERATOR=${encodeURIComponent(viewStateGenerator)}&__EVENTTARGET=${encodeURIComponent(eventTarget)}&__EVENTARGUMENT=${encodeURIComponent(eventArgument)}`;

            // 签到操作
            const signInResponse = await axios.post(signInUrl, postData, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    Cookie: token
                }
            });

            const resultPage = cheerio.load(signInResponse.data);
            const signMessage = resultPage('#lblprice').text(); // 检查是否有提示成功的消息

            const messageTitle = `账号 ${i + 1} 签到结果`;
            const messageContent = signMessage.includes('签到') || signMessage.includes('已签') ? 
                `账号 ${i + 1} 签到成功: ${signMessage}` : 
                `账号 ${i + 1} 签到失败: ${signMessage}`;

            console.log(messageContent);
            await sendPushplusMessage(messageTitle, messageContent);
        } catch (error) {
            const errorMessageTitle = `账号 ${i + 1} 请求出错`;
            const errorMessageContent = `账号 ${i + 1} 请求出错： ${error.message}`;
            console.error(errorMessageContent);
            await sendPushplusMessage(errorMessageTitle, errorMessageContent);
        }
    }
})();
