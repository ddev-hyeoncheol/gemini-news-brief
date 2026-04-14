import feedparser
import logging
import time
import hashlib
from datetime import datetime
from newspaper import Article, Config

# 1. 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class NewsScraper:
    def __init__(self):
        self.config = Config()
        self.config.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        self.config.request_timeout = 20
        self.sources = {
            "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
            "CNBC": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839069",
            "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
            "The Guardian": "https://www.theguardian.com/business/economics/rss",
        }

    def _generate_id(self, link):
        """URL을 기반으로 고유 ID 생성 (중복 방지)"""
        return hashlib.md5(link.encode("utf-8")).hexdigest()

    def _format_date(self, parsed_date):
        """RSS 날짜를 BigQuery TIMESTAMP 형식으로 변환"""
        try:
            return datetime(*parsed_date[:6]).isoformat()
        except:
            return datetime.utcnow().isoformat()

    def fetch_latest_news(self):
        all_articles = []
        logging.info("🚀 뉴스 수집 프로세스를 시작합니다.")

        for name, url in self.sources.items():
            logging.info(f"📡 {name} 피드 연결 중...")
            feed = feedparser.parse(url)

            if not feed.entries:
                logging.warning(f"⚠️ {name}: 새 기사가 없습니다.")
                continue

            # 각 매체당 최신 기사 1개만 샘플링 (테스트용)
            entry = feed.entries[0]

            # 기본 데이터 추출
            article_data = {
                "article_id": self._generate_id(entry.link),
                "source": name,
                "title": entry.title,
                "link": entry.link,
                "published_at": self._format_date(entry.get("published_parsed")),
                "content": "",
            }

            try:
                # 본문 추출
                article = Article(entry.link, config=self.config)
                article.download()
                article.parse()

                # 본문 정제 (공백 제거 등)
                content = article.text.strip()
                if content:
                    article_data["content"] = content
                    logging.info(
                        f"✅ {name}: '{article_data['title'][:20]}...' 수집 성공 ({len(content)}자)"
                    )
                    all_articles.append(article_data)
                else:
                    logging.warning(f"⚠️ {name}: 본문 내용이 비어있습니다.")

            except Exception as e:
                logging.error(f"❌ {name} 수집 중 오류 발생: {e}")

            time.sleep(1.5)  # 사이트 예의

        return all_articles


if __name__ == "__main__":
    scraper = NewsScraper()
    news_list = scraper.fetch_latest_news()

    print(f"\n✨ 총 {len(news_list)}개의 기사가 정제되었습니다.")
    for news in news_list:
        print(f"[{news['source']}] {news['title']} ({news['published_at']})")
