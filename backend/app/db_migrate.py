"""SQLite：为已存在的表补齐 ORM 里新增列（db.create_all 不会 ALTER 旧表）。"""

from sqlalchemy import inspect, text


def migrate_sqlite(engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    insp = inspect(engine)
    if "rss_wechat_article" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("rss_wechat_article")}

    with engine.begin() as conn:
        if "information_source_id" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE rss_wechat_article "
                    "ADD COLUMN information_source_id INTEGER"
                )
            )
        if "aid" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE rss_wechat_article "
                    "ADD COLUMN aid VARCHAR(255) NOT NULL DEFAULT ''"
                )
            )
        if "link" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE rss_wechat_article "
                    "ADD COLUMN link VARCHAR(512)"
                )
            )

        # BaseModel 列（若表是更老的结构）
        if "created_at" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE rss_wechat_article "
                    "ADD COLUMN created_at DATETIME"
                )
            )
        if "updated_at" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE rss_wechat_article "
                    "ADD COLUMN updated_at DATETIME"
                )
            )
        if "system_status" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE rss_wechat_article "
                    "ADD COLUMN system_status BOOLEAN DEFAULT 1"
                )
            )

        # 联合唯一：若尚无同名索引则建（旧表可能没有）
        idx_rows = conn.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND name='uq_rss_wechat_article_source_aid'"
            )
        ).fetchall()
        if not idx_rows:
            try:
                conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS "
                        "uq_rss_wechat_article_source_aid "
                        "ON rss_wechat_article (information_source_id, aid)"
                    )
                )
            except Exception:
                pass
