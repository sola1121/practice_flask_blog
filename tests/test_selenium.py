import os
import re
import unittest
import threading

from selenium import webdriver

from ..app import create_app, db
from ..app.models import Role, User
from ..app import fake_data

class SeleniumTestCase(unittest.TestCase):
    client = None

    @classmethod
    def setUpClass(cls):
        # 启动Chrome
        options = webdriver.ChromeOptions()
        options.add_argument("headless")
        try:
            # 创建webdriver客户端, 指定chromedrive位置, 并配置设置
            cls.client = webdriver.Chrome(executable_path=os.environ.get("chrome_driver"), chrome_options=options)
        except:
            pass
        
        # 如果无法启动浏览器, 跳过这些测试
        if cls.client:
            # 创建应用
            cls.app = create_app("testing")
            cls.app_context = cls.app.app_context()
            cls.app_context.push()

            # 禁止日志
            import logging
            logger = logging.getLogger("werkzeug")
            logger.setLevel("ERROR")

            # 创建数据库, 并用一些虚拟数据填充
            db.create_all()
            fake_data.create_users(10)
            fake_data.create_posts(10)

            # 添加管理员
            admin_role = Role.query.filter_by(name='Administrator').first()
            admin = User(
                email="john@example.com",
                username="john", password="cat",
                role=admin_role, confirmed=True,
            )
            db.session.add(admin)
            db.session.commit()

            # 在一个线程中启动Flask服务器
            cls.server_thread = threading.Tread(
                target=cls.app.run, kwargs={"debug": "false", "use_reloader": False, "use_debuger": False}
            )
            cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        if cls.client:
            # 关闭Flask服务器
            cls.client.get("http://localhost:5000/shutdown")
            cls.client.quit()
            cls.server_thread.join()
            
            # 销毁数据库
            db.drop_all()
            db.session.remove()

            # 删除应用上下文
            cls.app_context.pop()

    def setUp(self):
        if not self.client:
            self.skipTest("Web browser not available")
    
    def tearDown(self):
        pass

    def test_admin_home_page(self):
        # 进入首页
        self.client.get("http://localhost:5000/")
        self.assertTrue(re.search("Hello,\s+Stranger*", self.client.page_source))
        # 进入登录页面
        self.client.find_element_by_link_text("login in").click()
        self.assertIn("<h1>Login</h1>", self.client.page_source)
        # 登录
        self.client.find_element_by_name("email").send_keys("john@example.com")
        self.client.find_element_by_name("password").send_keys("cat")
        self.client.find_element_by_name("submit").click()
        self.assertTrue(re.search("Hello,+sjohn*", self.client.page_source))
        # 进入用户资料页
        self.client.find_element_by_link_text("Profile").click()
        self.assertIn("<h1>john</h1>", self.client.page_source)
