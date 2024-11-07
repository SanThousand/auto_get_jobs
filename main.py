from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from aiconfig import ai_response, ai_hr
from dotenv import load_dotenv
import os
import random
import time
import json

load_dotenv()

options = webdriver.ChromeOptions()
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option('excludeSwitches', ['enable-automation'])
driver_path = os.path.join("chromedriver", "chromedriver.exe")
wb = webdriver.Chrome(service=Service(driver_path),options=options)

def login():
    """
    登录BOSS直聘
    """
    #登录URl
    login_url = "https://www.zhipin.com/web/user/?ka=header-login"
    wb.get(login_url)
    #等待用户登录登录成功跳转主页
    try:
        print(f"等待登陆...")
        WebDriverWait(wb, 60).until(
            EC.url_to_be(("https://www.zhipin.com/web/geek/job-recommend")) or
            EC.url_to_be(("https://www.zhipin.com"))
        )
        print(f"登陆成功，自动跳转到主页。")
    except Exception as e:
        print(f"页面跳转失败: {e}")
    return
def search(query, city, degree = None):
    """
    构造搜索URL
    :param query: 职位
    :param city: 城市
    """
    
    cityid = get_cityid(city)
    serch_url = f"https://www.zhipin.com/web/geek/job?query={query}&city={cityid}"
    if degree:
        serch_url += f"&degree={degree}"
    wb.get(serch_url)
    try:
        print(f"等待页面加载完成...")
        WebDriverWait(wb, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "search-job-result"))
        )
        print(f"页面加载完成，开始筛选岗位。")
    except Exception as e:
        print(f"页面加载失败: {e}")
    return

def get_cityid(city):
    """
    获取城市的ID
    """
    cityid_dict = json.load(open("city_list.json", "r", encoding="utf-8"))
    cityid = cityid_dict[city]
    
    return cityid

def get_job_info():
    """
    获取岗位信息
    """
    jobs = []
    while True:
        
        WebDriverWait(wb, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-name"))
        )
        time.sleep(random.uniform(3, 5))
        html_content = wb.page_source 
        soup = BeautifulSoup(html_content, "html.parser")
        #找到所有的岗位信息块
        job_cards = soup.find_all('li', class_='job-card-wrapper')
        # print(job_cards)
        
        for job_card in job_cards:
            #岗位名称
            job_name = job_card.find('span', class_="job-name").text.strip()
            # print(job_name)
            #薪资
            job_salary = job_card.find('span', class_="salary").text.strip()
            #岗位链接
            job_link = job_card.find('a', class_ = 'job-card-left')['href']
            
            jobs.append({
                'job_name': job_name,
                'job_salary': job_salary,
                'job_link': job_link
            })
            # print(f"当前岗位数量：{len(jobs)}")
            
        # 下一页按钮的位置
        try:
            next_page_button = wb.find_element(By.CLASS_NAME, "ui-icon-arrow-right")
            print("开始采集下一页")
            if "disabled" in next_page_button.find_element(By.XPATH, "..").get_attribute("class"):
                print("没有下一页了，退出循环。")
                break
            wb.execute_script("arguments[0].click();", next_page_button)
        except:
            print("没有下一页按钮，退出循环。")
            break    
    return jobs


def check_position_match(query, my_job_salary):
    """
    检索岗位是否匹配
    query: 岗位名称
    my_job_salary: 我的期望薪资
    """
    jobs = get_job_info()
    print(f"根据当前数据，城市中总共有 {len(jobs)} 个岗位可供选择。")
    position_matchs = []
    for job in jobs:
        job_name = job['job_name']
        job_salary = job['job_salary']

        content=f'你是一个经验丰富的HR，你的任务是判断当前招聘岗位和薪资水平是否和我所期望的岗位匹配，如果匹配输出true，不匹配则输出false，除了true和false不要输出任何多余的内容，不要对基本信息讨论。以下是基本信息：当前招聘的岗位为“{job_name}”，招聘的岗位薪资为“{job_salary}k”，我所期望的岗位为“{query}”，最低薪资为“{my_job_salary}k”。'
        ai_res = ai_response(content)
        print(f"招聘岗位: {job_name}  |  期望岗位: {query}  |  AI判断结果: {ai_res}")
        if ai_res.lower() == "true":
            position_matchs.append(job)
            # print(position_matchs)
    print(f"根据当前数据，系统筛选出符合要求的岗位总数为: {len(position_matchs)} 个。")
    return position_matchs


def active_hr(boss_url, query, my_job_salary):
    """
    获取活跃的HR,HR活跃开始分析工作
    boss_url: 招聘平台链接
    query: 岗位名称
    my_job_salary: 我的期望薪资
    """
    # active_hr_jobs = []
    #获取工作列表
    position_matchs = check_position_match(query, my_job_salary)
    # print(f"当前有效岗位数量为：{len(position_matchs)},-----开始处理")
    #获取单个工作详情页
    for job in position_matchs:
        job_link = job['job_link']
        job_detail = boss_url + job_link
        wb.get(job_detail)
        WebDriverWait(wb, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-boss-info"))
        )
        #bs4解析页面hr活跃度
        html_content = wb.page_source
        soup = BeautifulSoup(html_content, "html.parser")
        try:
            if is_hr_online(soup):
                chat_with_hr(soup)
                print(f"当前HR在线，开始投递")
            else:
                hr_active_time = soup.find('span', class_='boss-active-time').text.strip()
                # print(f"HR活跃时间为：{hr_active_time}")
                if hr_active_time not in ["本月活跃", "2月内活跃","3月内活跃", "4月内活跃", "5月内活跃", "半年前活跃"]:
                    chat_with_hr(soup)
                    print(f"HR活跃程度为：{hr_active_time},开始分析简历...")
                 #HR在线率搞获取岗位名称开始对比
                 
            # active_hr_jobs.append(job)
            # time.sleep(5)
        except:
            print(f"解析失败，跳过当前岗位。")
            time.sleep(5)
            continue
    
    # return active_hr_jobs
def is_hr_online(soup):
    hr_online_tag = soup.find('span', class_='boss-online-tag')
    if hr_online_tag and '在线' in hr_online_tag.text.strip():
        return True
    return False

def chat_with_hr(soup):
    chat_check = check_job_match(soup).strip()
    print(f"是否推荐:{chat_check}")
    WebDriverWait(wb, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn.btn-startchat"))
    )
    if chat_check.lower() == "true":
        startchat_button = wb.find_element(By.CSS_SELECTOR, ".btn.btn-startchat")
        print(f"找到按钮: {startchat_button.text.strip()}")
        if startchat_button.is_enabled() and startchat_button.is_displayed():
            print("按钮可点击")
            startchat_button = wb.find_element(By.CSS_SELECTOR, ".btn.btn-startchat")
            wb.execute_script("arguments[0].scrollIntoView(true);", startchat_button)
            startchat_button.click()
            time.sleep(8)
        else:
            print("按钮不可点击")
    return

def check_job_match(soup):
    """
    检测岗位内容是否匹配
    """
    user_requirements = get_user_requirements()
    job_requirements = soup.find('div', class_='job-sec-text').text.strip()
    first_response = ai_hr(job_requirements, user_requirements)
    final_analysis = ai_hr(job_requirements, user_requirements, first_response, data_analysis=True)
    print(f"初步分析结果:{first_response}")
    print(f"-----------------------------------------------------------------------------")
    return final_analysis

def get_user_requirements():
    """
    获取用户简历
    """
    file_path = os.path.join("user_requirements.txt")
    if not os.path.exists(file_path):
        raise FileNotFoundError("用户简历文件不存在，请先创建。")
    with open(file_path, "r", encoding="utf-8") as f:
        user_requirements = f.read().strip()
        # print(user_requirements)
    return user_requirements
    

if __name__ == "__main__":
    querys = os.getenv("QUERYS").strip().split(",")
    citys = os.getenv("CITYS").strip().split(",")
    my_job_salary = os.getenv("MY_JOB_SALARY")
    boss_url = "https://www.zhipin.com"
    login()
    for city in citys:
        for query in querys:
            degree = os.getenv("DEGREE")
            search(query, city, degree)
            print(f"当前分析岗位：{query}，当前分析城市为：{city}")
            active_hr(boss_url, query, my_job_salary)
    wb.quit()