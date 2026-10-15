# 実行したコマンド(合言葉の値は変数 P / PW のみ。値は出していない)
H="/Volumes/HIGHLIFEJPN HDD/claude-archive.sparsebundle"
鍵作成: PW=$(openssl rand -base64 33) && security add-generic-password -s claude-archive-hdd -a archive -w "$PW"; unset PW
取得: P=$(security find-generic-password -s claude-archive-hdd -a archive -w)   # $() が末尾改行を除去。tr -d なし。長さ=44
create: printf '%s' "$P" | hdiutil create -type SPARSEBUNDLE -fs APFS -encryption AES-256 -stdinpass -size 4t -volname ClaudeArchive "$H"
attach: printf '%s' "$P" | hdiutil attach -stdinpass -nobrowse "$H"
(printf '%s' なので末尾改行なし。tr 等の加工なし。create と attach は同一シェル内で同じ P を使用)
