"""
闲鱼 API 封装模块
基于 XianyuAutoAgent 项目的 API 实现
"""
import time
import os
import re
import sys

import requests
from loguru import logger
from .xianyu_utils import generate_sign


class XianyuAPI:
    """闲鱼 API 封装类"""
    
    def __init__(self, cookies_str: str = None):
        self.url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/'
        self.session = requests.Session()
        self.session.headers.update({
            'accept': 'application/json',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cache-control': 'no-cache',
            'origin': 'https://www.goofish.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://www.goofish.com/',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        })
        
        if cookies_str:
            self.set_cookies(cookies_str)
    
    def set_cookies(self, cookies_str: str):
        """设置 Cookie"""
        from http.cookies import SimpleCookie
        cookie = SimpleCookie()
        cookie.load(cookies_str)
        
        self.session.cookies.clear()
        for key, morsel in cookie.items():
            self.session.cookies.set(key, morsel.value, domain='.goofish.com')
        
        # 清理重复 Cookie
        self._clear_duplicate_cookies()
    
    def _clear_duplicate_cookies(self):
        """清理重复的 cookies"""
        new_jar = requests.cookies.RequestsCookieJar()
        added_cookies = set()
        
        cookie_list = list(self.session.cookies)
        cookie_list.reverse()
        
        for cookie in cookie_list:
            if cookie.name not in added_cookies:
                new_jar.set_cookie(cookie)
                added_cookies.add(cookie.name)
        
        self.session.cookies = new_jar
    
    def get_cookies_str(self) -> str:
        """获取 Cookie 字符串"""
        return '; '.join([f"{cookie.name}={cookie.value}" for cookie in self.session.cookies])
    
    def has_login(self, retry_count: int = 0) -> bool:
        """检查登录状态"""
        if retry_count >= 2:
            logger.error("登录检查失败，重试次数过多")
            return False
            
        try:
            url = 'https://passport.goofish.com/newlogin/hasLogin.do'
            params = {
                'appName': 'xianyu',
                'fromSite': '77'
            }
            data = {
                'hid': self.session.cookies.get('unb', ''),
                'ltl': 'true',
                'appName': 'xianyu',
                'appEntrance': 'web',
                '_csrf_token': self.session.cookies.get('XSRF-TOKEN', ''),
                'umidToken': '',
                'hsiz': self.session.cookies.get('cookie2', ''),
                'bizParams': 'taobaoBizLoginFrom=web',
                'mainPage': 'false',
                'isMobile': 'false',
                'lang': 'zh_CN',
                'returnUrl': '',
                'fromSite': '77',
                'isIframe': 'true',
                'documentReferer': 'https://www.goofish.com/',
                'defaultView': 'hasLogin',
                'umidTag': 'SERVER',
                'deviceId': self.session.cookies.get('cna', '')
            }
            
            response = self.session.post(url, params=params, data=data)
            res_json = response.json()
            
            if res_json.get('content', {}).get('success'):
                logger.debug("登录成功")
                self._clear_duplicate_cookies()
                return True
            else:
                logger.warning(f"登录失败: {res_json}")
                time.sleep(0.5)
                return self.has_login(retry_count + 1)
                
        except Exception as e:
            logger.error(f"登录请求异常: {str(e)}")
            time.sleep(0.5)
            return self.has_login(retry_count + 1)
    
    def get_token(self, device_id: str, retry_count: int = 0, _login_refreshed: bool = False):
        """获取登录 Token"""
        if retry_count >= 2:
            if not _login_refreshed:
                logger.warning("获取 token 失败，尝试重新登录")
                if self.has_login():
                    return self.get_token(device_id, 0, _login_refreshed=True)
            logger.error("获取 Token 失败，Cookie 可能已失效")
            return None
            
        params = {
            'jsv': '2.7.2',
            'appKey': '34839810',
            't': str(int(time.time()) * 1000),
            'sign': '',
            'v': '1.0',
            'type': 'originaljson',
            'accountSite': 'xianyu',
            'dataType': 'json',
            'timeout': '20000',
            'api': 'mtop.taobao.idlemessage.pc.login.token',
            'sessionOption': 'AutoLoginOnly',
            'spm_cnt': 'a21ybx.im.0.0',
        }
        
        data_val = '{"appKey":"444e9908a51d1cb236a27862abc769c9","deviceId":"' + device_id + '"}'
        data = {'data': data_val}
        
        token = self.session.cookies.get('_m_h5_tk', '').split('_')[0]
        sign = generate_sign(params['t'], token, data_val)
        params['sign'] = sign
        
        try:
            response = self.session.post(
                'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/', 
                params=params, 
                data=data
            )
            res_json = response.json()
            
            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                    logger.warning(f"Token API 调用失败: {ret_value}")
                    if 'Set-Cookie' in response.headers:
                        self._clear_duplicate_cookies()
                    # RGV587_ERROR is rate-limiting/risk control, wait longer
                    delay = 2.0 if any('RGV587_ERROR' in ret for ret in ret_value) else 0.5
                    time.sleep(delay)
                    return self.get_token(device_id, retry_count + 1, _login_refreshed)
                else:
                    logger.info("Token 获取成功")
                    return res_json
            else:
                logger.error(f"Token API 返回格式异常: {res_json}")
                return self.get_token(device_id, retry_count + 1, _login_refreshed)

        except Exception as e:
            logger.error(f"Token API 请求异常: {str(e)}")
            time.sleep(0.5)
            return self.get_token(device_id, retry_count + 1, _login_refreshed)
    
    def get_item_info(self, item_id: str, retry_count: int = 0):
        """获取商品详情"""
        if retry_count >= 3:
            logger.error("获取商品信息失败，重试次数过多")
            return {"error": "获取商品信息失败，重试次数过多"}
            
        params = {
            'jsv': '2.7.2',
            'appKey': '34839810',
            't': str(int(time.time()) * 1000),
            'sign': '',
            'v': '1.0',
            'type': 'originaljson',
            'accountSite': 'xianyu',
            'dataType': 'json',
            'timeout': '20000',
            'api': 'mtop.taobao.idle.pc.detail',
            'sessionOption': 'AutoLoginOnly',
            'spm_cnt': 'a21ybx.im.0.0',
        }
        
        data_val = '{"itemId":"' + item_id + '"}'
        data = {'data': data_val}
        
        token = self.session.cookies.get('_m_h5_tk', '').split('_')[0]
        sign = generate_sign(params['t'], token, data_val)
        params['sign'] = sign
        
        try:
            response = self.session.post(
                'https://h5api.m.goofish.com/h5/mtop.taobao.idle.pc.detail/1.0/', 
                params=params, 
                data=data
            )
            
            res_json = response.json()
            
            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                    logger.warning(f"商品信息 API 调用失败: {ret_value}")
                    if 'Set-Cookie' in response.headers:
                        self._clear_duplicate_cookies()
                    time.sleep(0.5)
                    return self.get_item_info(item_id, retry_count + 1)
                else:
                    logger.debug(f"商品信息获取成功: {item_id}")
                    return res_json
            else:
                logger.error(f"商品信息 API 返回格式异常: {res_json}")
                return self.get_item_info(item_id, retry_count + 1)
                
        except Exception as e:
            logger.error(f"商品信息 API 请求异常: {str(e)}")
            time.sleep(0.5)
            return self.get_item_info(item_id, retry_count + 1)
    
    def get_user_id(self) -> str:
        """获取当前用户 ID"""
        return self.session.cookies.get('unb', '')
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return bool(self.session.cookies.get('unb', '')) and self.has_login()