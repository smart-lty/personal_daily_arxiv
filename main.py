import arxiv
import tqdm
import json
from openai import OpenAI

# 替换为你的DeepSeek Chat API的URL和API密钥
DEEPSEEK_CHAT_API_KEY = "{YOUR API KEY}"
DEEPSEEK_CHAT_BASE_URL = "https://api.deepseek.com"
client = OpenAI(api_key=DEEPSEEK_CHAT_API_KEY, base_url=DEEPSEEK_CHAT_BASE_URL)
FETCH_NUM = 100
KEY_WORDS = ["speculative decoding"]

def fetch_arxiv_papers(query, max_results=10):
    arxiv_client = arxiv.Client(page_size=max_results, delay_seconds=3, num_retries=3)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )
    
    papers = []
    for result in arxiv_client.results(search):
        summary = result.summary.replace('\n', ' ').strip()  # 去除换行符并去除首尾空白
        papers.append({
            "title": result.title,
            "summary": summary,
            "authors": ", ".join([author.name for author in result.authors]),
            "published": result.published.strftime("%Y-%m-%d"),
            "link": result.entry_id
        })
    
    print(f"Successfully fetching {len(papers)} papers.")
    return papers

def generate_tldr_and_summary(summary):
    res = []
    messages = [{"role": "user", "content": f"请将以下内容翻译成中文：{summary}"}]
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages
    )
    res.append(response.choices[0].message.content.strip())

    messages = [{"role": "user", "content": f"请使用一句话总结以下内容(英文)：{summary}"}]
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages
    )
    res.append(response.choices[0].message.content.strip())

    messages = [{"role": "user", "content": f"请使用一句话总结以下内容(中文)：{summary}"}]
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages
    )
    res.append(response.choices[0].message.content.strip())
    return res

def save_to_markdown(papers, filename):
    with open(filename, 'w') as f:
        f.write("| Title | Authors | Published | Link | TL, DR(英文) | TL, DR(中文) |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for paper in papers:
            f.write(f"| [{paper['title']}]({paper['link']}) | {paper['authors']} | {paper['published']} | [Link]({paper['link']}) | {paper['tldr_en']} | {paper['tldr_zh']} |\n")
        
        f.write("\n\n")
        
        for paper in papers:
            f.write(f"### {paper['title']}\n")
            f.write(f"- **Authors**: {paper['authors']}\n")
            f.write(f"- **Published**: {paper['published']}\n")
            f.write(f"- **Link**: [{paper['link']}]({paper['link']})\n")
            f.write(f"- **Summary**: {paper['summary']}\n\n")
            f.write(f"- **中文摘要**: {paper['chinese_summary']}\n\n")

def read_existing_papers(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_papers_to_json(papers, filename):
    with open(filename, 'w') as f:
        json.dump(papers, f, indent=4)

def main():
    # 使用更精确的查询语法
    key_words = KEY_WORDS
    for kw in key_words:
        query = f"ti:\"{kw}\" OR abs:\"{kw}\""
        json_filename = f"{kw.replace(' ', '_')}_papers.json"
        md_filename = f"{kw.replace(' ', '_')}_papers.md"
        existing_papers = read_existing_papers(json_filename)
        new_papers = fetch_arxiv_papers(query, FETCH_NUM)
    
        if new_papers:
            # 检查新论文是否已经存在于现有论文中
            existing_authors = {paper['authors'] for paper in existing_papers}
            new_papers = [paper for paper in new_papers if paper['authors'] not in existing_authors]

            if new_papers:
                # 合并新旧论文并按时间排序
                all_papers = existing_papers + new_papers
                all_papers.sort(key=lambda x: x['published'], reverse=True)

                # 生成TL, DR和中文摘要
                for paper in tqdm.tqdm(all_papers):
                    if 'tldr_en' not in paper:
                        tldr_and_summary = generate_tldr_and_summary(paper['summary'])
                        paper['chinese_summary'] = tldr_and_summary[0]
                        paper['tldr_en'] = tldr_and_summary[1]
                        paper['tldr_zh'] = tldr_and_summary[2]

                # 保存所有论文信息到JSON文件
                save_papers_to_json(all_papers, json_filename)

                # 保存所有论文信息到Markdown文件
                save_to_markdown(all_papers, md_filename)

                print(f"Saved {len(new_papers)} new papers to {md_filename}")
            else:
                print("No new papers found.")
        else:
            print("No new papers found.")

if __name__ == "__main__":
    main()