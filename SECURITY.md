# Security

Controller credentials are secrets even when the certificate portion is sometimes described as public identity data. Do not submit keys, serials, certificate signatures, generated headers, challenge dumps, or firmware binaries to issues or pull requests.

Compiled firmware embeds the credential set. This repository intentionally publishes source only.

If credentials are accidentally committed, remove public access immediately and treat the identity as exposed. Rewriting Git history does not guarantee removal from forks, caches, or downloaded clones.

Only use credentials extracted from hardware you own and where applicable law and platform terms permit it. This project does not include an extraction method.

