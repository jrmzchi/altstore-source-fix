# AltStore Source Fix

將 [Moe AltStore](https://github.com/MountainofPenguin/moe-altstore) 的來源自動去除重複 Bundle ID，產生可供 AltStore 訂閱的 JSON。

## 訂閱網址

`https://raw.githubusercontent.com/jrmzchi/altstore-source-fix/main/apps.json`

請等第一次 GitHub Actions 成功執行、產生 apps.json 後，再加入 AltStore → Sources → +。

## 運作方式

- 每日 UTC 04:20 自動檢查上游，也可於 Actions → Update AltStore Source → Run workflow 手動執行。
- 保留上游 IPA 下載網址，不重新打包或簽署 IPA。
- 同一 Bundle ID 預設選擇較新版本；可透過 config.json 的 preferred_names 指定保留的 App 名稱。
- 驗證資料格式、URL、唯一性；若上游異常，工作流程失敗且不提交。
- dedup-report.json 記錄被排除的重複項目。
- 若 JSON 無變化，不產生 Commit。

## 本機測試

```bash
python -m unittest discover -s tests -v
python scripts/update.py
```

## 自訂選擇

在 `config.json` 的 `preferred_names` 中加入 Bundle ID 與欲保留的名稱，例如：

```json
{"preferred_names":{"com.example.app":"Preferred App"},"min_retained_ratio":0.6}
```

若上游 App 名稱不符，會依版本與日期自動選擇。

## 失敗與還原

在 GitHub Actions 的執行紀錄查看錯誤；失敗時不提交新 JSON。若要還原，於 GitHub 的 apps.json 歷史紀錄選擇上一個正常 Commit 還原。首次執行前尚無可供還原的基準。

## 限制

本專案只修復來源資料重複，不保證 IPA 的安全性、可安裝性、權限宣告完整性或 AltStore 的所有其他檢查。上游提供的修改版 IPA 並非本專案審核或背書。
