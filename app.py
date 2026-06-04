import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

APP_TITLE = "7 月吃飯時間統計"
DB_PATH = Path("availability.db")

YEAR = 2026
START_DATE = date(YEAR, 7, 1)
END_DATE = date(YEAR, 7, 31)
SLOTS = ["午餐", "晚餐"]


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            pin TEXT NOT NULL,
            day TEXT NOT NULL,
            slot TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(name, pin, day, slot)
        )
    """)
    return conn


def all_days():
    return pd.date_range(START_DATE, END_DATE, freq="D").date


def day_label(d: date) -> str:
    weekday_map = ["一", "二", "三", "四", "五", "六", "日"]
    return f"{d.strftime('%m/%d')}（{weekday_map[d.weekday()]}）"


def load_all(conn):
    return pd.read_sql_query(
        "SELECT name, pin, day, slot, updated_at FROM availability ORDER BY day, slot, name",
        conn,
    )


def load_user(conn, name, pin):
    return pd.read_sql_query(
        "SELECT day, slot FROM availability WHERE name = ? AND pin = ?",
        conn,
        params=(name.strip(), pin.strip()),
    )


def replace_user_availability(conn, name, pin, selected_pairs):
    now = datetime.now().isoformat(timespec="seconds")
    name = name.strip()
    pin = pin.strip()

    with conn:
        conn.execute("DELETE FROM availability WHERE name = ? AND pin = ?", (name, pin))
        conn.executemany(
            """
            INSERT INTO availability (name, pin, day, slot, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(name, pin, d, s, now, now) for d, s in selected_pairs],
        )


def delete_user(conn, name, pin):
    with conn:
        cur = conn.execute("DELETE FROM availability WHERE name = ? AND pin = ?", (name.strip(), pin.strip()))
    return cur.rowcount


def overview_table(df):
    if df.empty:
        return pd.DataFrame(columns=["日期", "時段", "可出席人數", "可出席名單"])

    grouped = (
        df.groupby(["day", "slot"])["name"]
        .apply(lambda x: sorted(set(x)))
        .reset_index(name="names")
    )
    grouped["可出席人數"] = grouped["names"].apply(len)
    grouped["可出席名單"] = grouped["names"].apply(lambda xs: "、".join(xs))
    grouped["日期"] = pd.to_datetime(grouped["day"]).dt.date.apply(day_label)
    grouped["時段"] = grouped["slot"]

    slot_order = {"午餐": 0, "晚餐": 1}
    grouped["slot_order"] = grouped["slot"].map(slot_order)

    return grouped.sort_values(
        ["可出席人數", "day", "slot_order"],
        ascending=[False, True, True],
    )[["日期", "時段", "可出席人數", "可出席名單"]]


def participant_summary(df):
    if df.empty:
        return pd.DataFrame(columns=["姓名", "填寫數量", "最後更新"])

    out = (
        df.groupby("name")
        .agg(
            填寫數量=("slot", "count"),
            最後更新=("updated_at", "max"),
        )
        .reset_index()
        .rename(columns={"name": "姓名"})
        .sort_values(["填寫數量", "姓名"], ascending=[False, True])
    )
    return out


st.set_page_config(page_title=APP_TITLE, page_icon="🍽️", layout="wide")
st.title(APP_TITLE)
st.caption("填寫 7/1–7/31 的午餐、晚餐可出席時間。用姓名＋編輯 PIN 可以修改或刪除自己的資料。")

conn = get_conn()
df_all = load_all(conn)

tab_fill, tab_overview, tab_admin = st.tabs(["填寫 / 修改", "總覽", "刪除自己的資料"])

with tab_fill:
    st.subheader("填寫或修改我的時間")

    c1, c2 = st.columns([2, 1])
    with c1:
        name = st.text_input("姓名", placeholder="例如：Howard")
    with c2:
        pin = st.text_input("編輯 PIN", type="password", placeholder="自己設定 4–8 碼即可")

    if name.strip() and pin.strip():
        user_df = load_user(conn, name, pin)
        existing = set(zip(user_df["day"], user_df["slot"])) if not user_df.empty else set()

        st.write("勾選你可以吃飯的時間：")

        selected = []
        days = list(all_days())

        header_cols = st.columns([1.6, 1, 1])
        header_cols[0].markdown("**日期**")
        header_cols[1].markdown("**午餐**")
        header_cols[2].markdown("**晚餐**")

        for d in days:
            cols = st.columns([1.6, 1, 1])
            cols[0].write(day_label(d))
            d_str = d.isoformat()

            for i, slot in enumerate(SLOTS, start=1):
                key = f"{name}_{pin}_{d_str}_{slot}"
                checked = (d_str, slot) in existing
                if cols[i].checkbox(slot, value=checked, key=key, label_visibility="collapsed"):
                    selected.append((d_str, slot))

        if st.button("儲存我的時間", type="primary"):
            if len(name.strip()) == 0 or len(pin.strip()) == 0:
                st.error("請輸入姓名與編輯 PIN。")
            else:
                replace_user_availability(conn, name, pin, selected)
                st.success(f"已儲存：{name.strip()}，共 {len(selected)} 個時段。")
                st.rerun()
    else:
        st.info("請先輸入姓名與編輯 PIN。之後用同一組姓名＋PIN 即可修改。")

with tab_overview:
    st.subheader("最多人可以的時間")

    df_all = load_all(conn)
    ov = overview_table(df_all)
    ps = participant_summary(df_all)

    m1, m2 = st.columns(2)
    m1.metric("已填寫人數", df_all["name"].nunique() if not df_all.empty else 0)
    m2.metric("總可出席時段數", len(df_all))

    if ov.empty:
        st.info("目前還沒有人填寫。")
    else:
        st.dataframe(ov, use_container_width=True, hide_index=True)

        max_n = int(ov["可出席人數"].max())
        best = ov[ov["可出席人數"] == max_n]
        st.markdown(f"**目前最佳交集：{max_n} 人可出席**")
        st.dataframe(best, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("已填寫名單")
    st.dataframe(ps, use_container_width=True, hide_index=True)

with tab_admin:
    st.subheader("刪除自己的資料")
    del_name = st.text_input("姓名", key="del_name")
    del_pin = st.text_input("編輯 PIN", type="password", key="del_pin")

    if st.button("刪除我的全部資料"):
        if not del_name.strip() or not del_pin.strip():
            st.error("請輸入姓名與編輯 PIN。")
        else:
            n = delete_user(conn, del_name, del_pin)
            if n > 0:
                st.success(f"已刪除 {del_name.strip()} 的 {n} 筆資料。")
                st.rerun()
            else:
                st.warning("找不到符合的資料。請確認姓名與 PIN 是否相同。")
