from DrissionPage import ChromiumPage, ChromiumOptions
from bs4 import BeautifulSoup
from aiconfig import ai_response, ai_hr
from dotenv import load_dotenv
import os
import random
import time
import json
import urllib.parse

load_dotenv()

co = ChromiumOptions()
co.set_user_data_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chrome_profile'))
co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36')
page = ChromiumPage(co)

def login():
    """
    登录BOSS直聘
    """
    login_url = "https://www.zhipin.com/web/user/?ka=header-login"
    page.get(login_url)
    try:
        print("等待登陆...")
        page.wait.url_change(login_url, timeout=60)
        print("登陆成功，自动跳转到主页。")
    except Exception as e:
        print(f"页面跳转失败: {e}")
    return

def search(query, city, degree = None):
    """
    构造搜索URL并打开搜索页
    :param query: 职位
    :param city: 城市
    """
    cityid = get_cityid(city)
    serch_url = f"https://www.zhipin.com/web/geek/jobs?query={urllib.parse.quote(query)}&city={cityid}"
    if degree:
        serch_url += f"&degree={degree}"
    page.get(serch_url)
    try:
        print("等待页面加载完成...")
        page.wait.ele_displayed('css:.job-list-container', timeout=60)
        print("页面加载完成，开始筛选岗位。")
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

def fetch_joblist(query, city, degree, page_num):
    """
    在页面上下文里同步调用搜索接口获取岗位JSON
    """
    q = urllib.parse.quote(query)
    js = f"""
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/wapi/zpgeek/search/joblist.json', false);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.send('page={page_num}&pageSize=15&city={city}&degree={degree}&query={q}&scene=1');
    return xhr.responseText;
    """
    return json.loads(page.run_js(js))

def get_job_info(query, cityid, degree, seen_links):
    """
    通过搜索接口获取岗位信息（薪资为真实文本）。
    seen_links 跨 query 共享：连续两页零新增时提前结束，避免重复采集。
    """
    jobs = []
    page_num = 1
    zero_new_pages = 0
    while True:
        try:
            data = fetch_joblist(query, cityid, degree, page_num)
            zp = data.get('zpData') or {}
            job_list = zp.get('jobList') or []
        except Exception as e:
            print(f"第{page_num}页接口调用失败: {e}")
            break
        new_count = 0
        for item in job_list:
            job_link = f"/job_detail/{item.get('encryptJobId')}.html"
            if job_link in seen_links:
                continue
            seen_links.add(job_link)
            new_count += 1
            jobs.append({
                'job_name': item.get('jobName', ''),
                'job_salary': item.get('salaryDesc', ''),
                'job_link': job_link,
                'skills': item.get('skills') or [],
                'city_name': item.get('cityName', ''),
                'brand_name': item.get('brandName', ''),
            })
        print(f"第{page_num}页返回 {len(job_list)} 个岗位，新增 {new_count} 个，累计 {len(jobs)} 个。")
        if not zp.get('hasMore'):
            print("没有更多页了，采集结束。")
            break
        if new_count == 0:
            zero_new_pages += 1
            if zero_new_pages >= 2:
                print("连续两页岗位全部重复，该关键词已被之前采集覆盖，提前结束。")
                break
        else:
            zero_new_pages = 0
        page_num += 1
        time.sleep(random.uniform(3, 6))
    return jobs


def ai_filter(jobs):
    """
    AI初筛：只保留适合第一份实习的Java/后端岗位
    """
    matched = []
    for job in jobs:
        job_name = job['job_name']
        job_salary = job['job_salary']

        if any(kw in job_name for kw in ['诚聘', '小朋友', '底薪', '月入', '福利', '五险一金', '晋升']):
            continue
        content=f'你是一个经验丰富的HR，你的任务是判断当前招聘岗位是否适合一个正在寻找第一份实习的2027届计算机专业本科在校生投递，适合输出true，不适合输出false，除了true和false不要输出任何多余的内容。判断标准：1.岗位须适合在校生投递：实习/校招/应届生岗位，或明确接受应届生、经验不限、应往届均可的初级正式岗位（岗位名含"实习"、"校招"、"应届"、"初级"、"助理"、"管培生"、"应往届均可"等字样，或薪资按天计算如"元/天"）；明确要求3年以上经验或高级/资深/架构师岗位输出false；2.岗位方向须为Java/后端/全栈开发相关；3.薪资只设下限不设上限（日薪不低于80元，或月薪不低于2K即可，薪资高不是否决理由）。当前招聘的岗位为"{job_name}"，招聘的岗位薪资为"{job_salary}"。'
        ai_res = ai_response(content)
        print(f"招聘岗位: {job_name}  |  薪资: {job_salary}  |  AI判断结果: {ai_res}")
        if ai_res and ai_res.lower() == "true":
            matched.append(job)
    print(f"AI初筛通过 {len(matched)} 个岗位。")
    return matched


# ---------- 投递 ----------

def deliver_jobs(selected_jobs):
    """
    对勾选的岗位逐个访问详情页，AI深度匹配后打招呼
    """
    boss_url = "https://www.zhipin.com"
    for job in selected_jobs:
        job_detail = boss_url + job['job_link']
        print(f"正在处理岗位: {job['job_name']} | {job['job_salary']}")
        try:
            page.get(job_detail)
            page.wait.ele_displayed('css:.job-boss-info', timeout=60)
            soup = BeautifulSoup(page.html, "html.parser")
            chat_with_hr(soup)
        except Exception as e:
            print(f"处理失败，跳过当前岗位: {e}")
            time.sleep(5)
            continue
        time.sleep(random.uniform(2, 5))

def chat_with_hr(soup):
    chat_check = check_job_match(soup).strip()
    print(f"AI分析投递结果:{chat_check}")
    print("-----------------------------------------------------------------------------")
    if chat_check.lower() == "true":
        try:
            startchat_button = page.ele('css:.btn-startchat', timeout=10)
            if startchat_button:
                startchat_button.click()
                print("已点击立即沟通。")
                time.sleep(8)
        except Exception as e:
            print(f"打招呼按钮点击失败: {e}")
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
    print("-----------------------------------------------------------------------------")
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
    return user_requirements


if __name__ == "__main__":
    querys = [q.strip() for q in os.getenv("QUERYS").strip().split(",")]
    citys = [c.strip() for c in os.getenv("CITYS").strip().split(",")]
    degree = os.getenv("DEGREE")
    login()

    all_jobs = []
    seen_links = set()
    for city in citys:
        for query in querys:
            cityid = get_cityid(city)
            search(query, city, degree)
            print(f"当前采集：{query}，当前城市为：{city}")
            jobs = get_job_info(query, cityid, degree, seen_links)
            all_jobs.extend(jobs)
            time.sleep(random.uniform(3, 6))
    print(f"共采集 {len(all_jobs)} 个不重复岗位。")

    matched = ai_filter(all_jobs)
    deliver_jobs(matched)
    page.quit()
