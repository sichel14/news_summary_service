"""启动时插入默认 RSS 信息源（幂等，按 rss_url 去重）。"""

from app.models.base import db
from app.models.information_source import InformationSource

# 机器之心主站 https://www.jiqizhixin.com/rss 已 302 到「数据服务」HTML，不再是 XML Feed。
# Synced（Synced Review）为同源英文站，RSS 稳定可用。
JIQIZHIXIN_SYNCED_RSS_URL = "https://syncedreview.com/feed/"

# 原版 trace 里 third_name=plink.anyfeeder.com，与 jiqizhixin 同属 RssWeb1SyncTask（feedparser）。
# 以下 URL 经请求验证返回 application/rss+xml。
ANYFEEDER_CNBETA_RSS_URL = "https://plink.anyfeeder.com/cnbeta"

_DEFAULT_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "机器之心 (Synced)",
        "Synced 英文站 RSS；legacy 中 third_name=www.jiqizhixin.com 亦为 feedparser 链路。",
        JIQIZHIXIN_SYNCED_RSS_URL,
    ),
    (
        "cnBeta (Anyfeeder)",
        "Anyfeeder 聚合全文 RSS；legacy 中 third_name=plink.anyfeeder.com，与上条同属 RssWeb1SyncTask。",
        ANYFEEDER_CNBETA_RSS_URL,
    ),
)


def ensure_default_sources() -> None:
    added = False
    for name, intro, rss_url in _DEFAULT_ROWS:
        if InformationSource.query.filter_by(rss_url=rss_url).first():
            continue
        db.session.add(
            InformationSource(name=name, intro=intro, rss_url=rss_url),
        )
        added = True
    if added:
        db.session.commit()
