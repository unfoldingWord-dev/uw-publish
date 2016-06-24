# Steps for Publishing translationAcademy

**Updated for tA version 5**

#### These are the repositories used as source for translationAcademy

* https://git.door43.org/Door43/en-ta-intro
* https://git.door43.org/Door43/en-ta-translate-vol1
* https://git.door43.org/Door43/en-ta-translate-vol2
* https://git.door43.org/Door43/en-ta-process
* https://git.door43.org/Door43/en-ta-checking-vol1
* https://git.door43.org/Door43/en-ta-checking-vol2
* https://git.door43.org/Door43/en-ta-audio
* https://git.door43.org/Door43/en-ta-gl


#### These are the instructions

1. Make sure the `meta.yaml` file in each repository is up-to-date. Pay attention to the version numbers and publish date.
1. Move the files from the previous version of tA to `/var/www/vhosts/api.unfoldingword.org/httpdocs/ta/txt/1/en/history/`.
1. Switch to sudo shell:
    ```
    sudo SSH_AUTH_SOCK=$SSH_AUTH_SOCK bash
    ```
1. Run this command one time for each repository. Watch for **WARNING** and **ERROR** messages that need your attention.
    ```
    python execute.py publish_ta -r https://git.door43.org/Door43/en-ta-intro
    ```
1. Copy the JSON files output by the above command to the API folder.
    ```
    cp output/{audio_2.json,checking_1.json,checking_2.json,gateway_3.json,intro_1.json,process_1.json,translate_1.json,translate_2.json} \
    /var/www/vhosts/api.unfoldingword.org/httpdocs/ta/txt/1/en/
    ```
1. Set file permissions.
    ```
    chown -R syncthing:syncthing /var/www/vhosts/api.unfoldingword.org/httpdocs/ta/txt/1/en/
    ```
1. In the `unfoldingWord.github.io` repository, update `_includes/ta_body.html` with the correct version number and PDF file name.
1. Commit the changes to the `master` branch and push to origin. This will update the `test.unfoldingword.org` site.
1. Have more than one person verify that `test.unfoldingword.org/academy/` is correct.
1. In the `unfoldingWord.github.io` repository, run `make publish` to push the changes to the production site.
