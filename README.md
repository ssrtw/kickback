# kickback

一個自用的 TUI 快速安裝腳本

## 執行

```sh
python3 -c "$(wget -q https://rawgit.com/ssrtw/kickback/main/kb.py -O -)"
python3 -c "$(wget -q https://tiny.one/kickbackpy -O -)"
```

## 使用方式

* `上下鍵` 移動
* `空白鍵` 選擇/取消
* `S` 執行選取的腳本
* `A` 全選選項
* `R` 反向選取
* `q` 結束腳本

## 自訂 script

在 `script.yml` 新增 `key` 為選項名稱，`value` 為要執行的 `script`

範例：
```yml
echo: |
  echo '努力、未來、A Beautiful Star'
```

新增後執行 `packer.py`，更新 `script` 到 `kb.py` 中

## TODO

用 `github workflow` 自動更新 `kb.py`