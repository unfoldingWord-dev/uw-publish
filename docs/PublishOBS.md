# Steps for Publishing OBS

**Don't forget to notify interested parties when finished, including publishing@unfoldingword.org.**

### From Dokuwiki pages (old instructions)
1. Create/Update https://door43.org/en/uwadmin/LANG_CODE/obs/status. Use https://door43.org/en/uwadmin/en/obs/status as a template.

    ```
    Be sure checking_level is in [1, 2, 3] and publish_date = Today (2016-06-14)
    ```
    
1. SSH to us.door43.org and `sudo SSH_AUTH_SOCK=$SSH_AUTH_SOCK bash`.
1. Create `noto-LANG_CODE.tex` in `tools/obs/tex`.
1. Run `tools/uw/publish.sh -L LANG_CODE`.
1. Run `python execute.py update_catalog`.
1. Run `python execute.py obs_in_progress`.
1. Run `chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/`.
1. On pki.unfoldingword.org run `sudo /root/tools/uw/sign.py`.
1. In the unfoldingword.github.io repository, you *must* add an entry to the "keep_files" directive in `_config.yml` when you want to add a new language for OBS.
1. Regenerate the uW website, `make publish`.


### From JSON file
1. Create/Update https://door43.org/en/uwadmin/LANG_CODE/obs/status. Use https://door43.org/en/uwadmin/en/obs/status as a template.

    ```
    Be sure checking_level is in [1, 2, 3] and publish_date = Today (2016-06-14)
    ```
1. Run `python execute.py clean_obs_json -f [path/to/obs-LANG_CODE.json]` to clean and format the file.
1. Clone the `github.com/unfoldingWord/obs-LANG_CODE` repository, or create it if needed.
1. Replace the `obs-LANG_CODE.json` file with the file created by step 1.
1. Edit `status-LANG_CODE.json` and update the information as needed.
1. Commit the changes and push to github.
1. Make sure the changes are pulled to `api.unfoldingword.org/obs/txt/1/LANG-CODE`.
1. Run `python execute.py import_obs -r https://github.com/unfoldingWord/obs-LANG_CODE -l LANG_CODE`.
1. Run `chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/`.
1. On pki.unfoldingword.org run `sudo /root/tools/uw/sign.py`.
1. In the unfoldingword.github.io repository, you *must* add an entry to the "keep_files" directive in `_config.yml` when you want to add a new language for OBS.
1. Regenerate the uW website, `make publish`.


### From a translationStudio repository
1. Create/Update https://door43.org/en/uwadmin/LANG_CODE/obs/status. Use https://door43.org/en/uwadmin/en/obs/status as a template.

    ```
    Be sure checking_level is in [1, 2, 3] and publish_date = Today (2016-06-14)
    ```
1. Fork the repository on git.door43.org
1. Create the `status.json` file in the repository root using `static/obs-status.json` as a template.
1. Push your changed back to git.door43.org.
1. Create `noto-LANG_CODE.tex` in `tools/obs/tex`.
1. SSH to us.door43.org and `sudo SSH_AUTH_SOCK=$SSH_AUTH_SOCK bash`.
1. Run `python execute.py publish_obs_from_ts -r https://git.door43.org/phillip-hopper/hmr_obs_text_obs`.
1. Run `chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/`.
1. On pki.unfoldingword.org run `sudo /root/tools/uw/sign.py`.
1. In the unfoldingword.github.io repository, you *must* add an entry to the "keep_files" directive in `_config.yml` when you want to add a new language for OBS.
1. Regenerate the uW website, `make publish`.


### From a Resource Container
1. Create/Update https://door43.org/en/uwadmin/LANG_CODE/obs/status. Use https://door43.org/en/uwadmin/en/obs/status as a template.

    ```
    Be sure checking_level is in [1, 2, 3] and publish_date = Today (2016-06-14)
    ```
1. Create `noto-LANG_CODE.tex` in `tools/obs/tex`.
1. SSH to us.door43.org and `sudo SSH_AUTH_SOCK=$SSH_AUTH_SOCK bash`.
1. Run `python execute.py publish_obs_from_rc -r https://git.door43.org/phillip-hopper/ne-obs.git`.
1. Run `chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/`.
1. On pki.unfoldingword.org run `sudo /root/tools/uw/sign.py`.
1. In the unfoldingword.github.io repository, you *must* add an entry to the "keep_files" directive in `_config.yml` when you want to add a new language for OBS.
1. Regenerate the uW website, `cd /var/www/projects/unfoldingWord.github.io/ && git pull && make publish`.
