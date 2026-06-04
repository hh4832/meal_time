# meal_time
meal time
7 月吃飯時間統計 App
功能：
7/1–7/31，每天午餐、晚餐可勾選
每個人用「姓名 + 編輯 PIN」修改自己的資料
可刪除自己的資料
總覽頁會顯示每個時段可出席人數與名單
自動排序最多人可出席的時間
本機執行
```bash
pip install -r requirements.txt
streamlit run app.py
```
部署建議
最快方式：Streamlit Community Cloud
建立一個 GitHub repository
放入 `app.py` 和 `requirements.txt`
到 Streamlit Community Cloud 建立 app
部署後把 app 連結傳給大家
注意：免費雲端服務如果重啟，SQLite 檔案可能有遺失風險。若是正式使用，建議改用 Supabase / PostgreSQL。
更穩方式：Render / Railway + PostgreSQL
正式多人使用建議改成 PostgreSQL，避免資料因雲端重啟遺失。
