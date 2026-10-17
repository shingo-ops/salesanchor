# openrsync の -R と /./ の実測メモ
- /usr/bin/rsync は openrsync (protocol 29, rsync 2.6.9 互換)。
- `rsync -a -R root/./rel dst/` の `/./` を無視し、dst 側に root からのフルパスが作られることを実測した。
- 対策: images は `bash -c 'cd root && rsync -a -R rel/ dst/'` で相対パスを保つ（scripts/claude-archive.sh の ca_copy_all）。
- `find` の `! -L` は効かないため `find -P -type f` を使う。
