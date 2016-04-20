# Steps for Publishing OBS

1. Create/Update https://door43.org/en/uwadmin/LANG_CODE/obs/status. Use https://door43.org/en/uwadmin/en/obs/status as a template.
1. SSH to us.door43.org and `sudo SSH_AUTH_SOCK=$SSH_AUTH_SOCK bash`.
1. Create `noto-LANG_CODE.tex` in `tools/obs/tex`.
1. Run `tools/uw/publish.sh -L LANG_CODE`.
1. On pki.unfoldingword.org run `sudo /root/tools/uw/sign.py`.
1. Regenerate the uW website, `make publish`.
