import requests
import json
import time
from dotenv import load_dotenv
import os

load_dotenv()

URL = os.getenv("API_URL").strip()
KEY = os.getenv("API_KEY").strip()
MODEL = os.getenv("MODEL").strip()

#检测匹配度用的
def ai_response(content):
    headers = {
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json"
    }
    data = {
        'model': MODEL,
        'temperature': 0.2,
        'max_tokens': 2048,
        'messages': [
            {
                "role": "user",
                "content": content
            }
        ]
    }
    for _ in range(5):
        try:
            response = requests.post(URL, data=json.dumps(data), headers=headers)
            response_json = response.json()
            if "choices" not in response_json:
                print(f"响应缺少 'choices' 字段，服务器返回: {response_json}")
                time.sleep(1)
                continue
            story = response_json["choices"][0]["message"]["content"]
            return story
        except requests.exceptions.RequestException as e:
            print(f"请求错误，正在重试... 错误原因{e}")
            time.sleep(1)
    return None


#模拟HR判断岗位是否合适。
def ai_hr(
    job_requirements, 
    user_requirements, 
    first_response = None, 
    data_analysis = False
):
    
    hr_prompt = """
    # Role: 经验丰富的HR\n
    \n
    ## Profile\n
    - author: suancaiyv\n
    - version: 1.0\n
    - language: 中文\n
    - description: 经验丰富的HR主管，根据公司发布的招聘需求和应聘者的简历信息，精准判断应聘者是否与岗位匹配，具备精准筛选判断能力。\n
    \n
    ## Goals\n
    1. 精准评估应聘者的简历内容，并根据公司发布的岗位要求进行匹配度分析。\n
    2. 基于简历和岗位描述的匹配情况，提供清晰的筛选建议。\n
    \n
    ## Skills\n
    1. 熟悉关键岗位的要求，能够准确提炼职位的关键技能和素质要求。\n
    2. 具备丰富的简历筛选与应聘者评估经验，能够从简历中识别核心技能和潜力。\n
    3. 准确判断应聘者与岗位的匹配度，依据岗位需求与应聘者简历中关键要素的对比。\n
    4. 有效沟通能力，能提供关于匹配结果的清晰判断依据。\n
    \n
    ## Rules\n
    1. 充分阅读并理解公司提供的招聘需求，包括工作经验、职位职责、所需技能、经验要求及软性条件。\n
    2. 仔细审阅应聘者的简历，重点关注其技能、工作经历、成就以及其他与职位要求相关的特质。\n
    3. 如果应聘者的背景与岗位要求存在显著差异，应以清晰的理由进行说明。\n
    4. 根据匹配度对候选人进行分类，提供推荐等级，并提供简洁的理由。\n
    \n
    ## OutputFormat:
    1.输出推荐指数。\n
    2.输出你给这个推荐指数以及理由（200字即可）。\n
    3.缺少的技术栈。\n
    4. 除了以上内容不要输出多余内容。 \n
    ## Workflows\n
    1. 获取公司的招聘需求，并熟悉岗位的核心技能和经验要求。\n
    2. 审阅应聘者的简历，识别其核心能力、关键经验及其与岗位要求的匹配点。注意：应聘者为在校生寻找第一份实习，实习/初级岗位对工作经验不作要求，缺少部分技术栈不影响推荐，只要核心技术方向（如Java后端）匹配即可。\n
    3. 对应聘者进行匹配分析，归纳其优劣势，并标注是否满足公司对该岗位的主要需求。实习/初级岗位不以工作经验为否决条件，主要考察技术方向相关性、基础能力与学习潜力。\n
    4. 根据分析结果提出招聘建议，并返回推荐指数0-1越高越推荐，便于后续招聘环节的决策。\n
    \n
    ## Init\n
    以“我已理解您的需求，请告诉我公司招聘需求以及应聘者的基本信息。”为开场白和用户对话，接下来遵循[workflow]流程开始工作。\n
    """
    
    
    
    headers = {
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json"
    }
    
    
    messages = [
        {
            "role": "system",
            "content": hr_prompt,
        },
        {
            "role": "assistant",
            "content": "我已理解您的需求，请告诉我公司岗位要求以及应聘者的基本信息。"
        },
        {
            "role": "user",
            "content": f"以下是公司的招聘岗位要求，如果你理解岗位要求，回复“理解即可”。\n 招聘岗位要求：{job_requirements}",
        },
        {
            "role": "assistant",
            "content": "理解"
        },
        {
            "role": "user",
            "content": f"以下是应聘者的基本简历，阅读并理解基本简历遵循[workflow]流程开始工作。\n 应聘者基本简历：{user_requirements}"
        }
    ]
    
    if first_response:
        messages.append({
            "role": "assistant",
            "content": first_response
        })
    if data_analysis:
        messages.append({
            "role": "user",
            "content": "结合以上信息和分析结果，精准判断应聘者是否与岗位匹配，注意应聘者是在校生找实习，实习/初级岗位匹配值大于“0.4”即可返回“true”，其他情况匹配值大于“0.5”返回“true”，否则返回“false”，不要对以上内容进行讨论和输出任何多余内容，只输出true或false即可。"
        })
    data = {
        'model': MODEL,
        'temperature': 0.2,
        'max_tokens': 4096,
        'messages': messages
    }
    for _ in range(5):
        try:
            response = requests.post(URL, data=json.dumps(data), headers=headers)
            response_json = response.json()
            if "choices" not in response_json:
                print(f"响应缺少 'choices' 字段，服务器返回: {response_json}")
                time.sleep(1)
                continue
            story = response.json()["choices"][0]["message"]["content"]
            return story
        except requests.exceptions.RequestException as e:
            print(f"请求错误，正在重试... 错误原因{e}")
            time.sleep(1)
    return None


if __name__ == "__main__":
    # 示例调用
    URL = "https://api.siliconflow.cn/v1/chat/completions"  # OpenAI API的实际端点
    KEY = "" # 替换为您的实际API密钥
    MODEL = "Vendor-A/Qwen/Qwen2.5-72B-Instruct"  # 使用的模型

    job_requirements = """
    岗位名称：Python开发工程师

    岗位职责：
    1. 负责公司后台系统的开发和维护；
    2. 参与系统架构设计，优化系统性能；
    3. 编写相关的技术文档。

    任职要求：
    1. 计算机相关专业本科及以上学历；
    2. 熟练掌握Python，熟悉Django或Flask框架；
    3. 有至少2年以上的Python开发经验；
    4. 熟悉数据库设计与优化，掌握MySQL或PostgreSQL；
    5. 良好的团队合作精神和沟通能力。
    """

    user_requirements = """
    姓名：张三
    学历：本科，市场营销专业
    工作经验：
    1. 在ABC公司担任Java开发工程师1年，主要负责Web应用的开发，使用Spring框架；
    2. 熟悉Oracle数据库，参与过数据库设计和优化项目；
    3. 有良好的团队协作经验，参与过多个跨部门项目的开发。

    技能：
    - 熟悉Java编程；
    - 了解Spring框架；
    - 掌握Oracle数据库；
    - 了解前端技术，如HTML、CSS、JavaScript。

    自我评价：
    热爱技术，学习能力强，善于解决复杂问题，具有良好的沟通和协作能力。
    """

    # 初步分析
    first_response = ai_hr(job_requirements, user_requirements)
    print("初步分析结果:", first_response)

    # # 最终分析
    final_analysis = ai_hr(job_requirements, user_requirements, first_response, data_analysis=True)
    print("最终分析结果:", final_analysis)
    