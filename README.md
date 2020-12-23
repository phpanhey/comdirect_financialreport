# readme boilerplate
this script generates an overview diagramm of your last 5 month income/expenses with the help of comdirect-rest api. you will be notified via telegram. very handy is a ssh shortcut on your phone in order to trigger the script on the fly. right now only pushtan is implemented. feel free to adapt the script to your needs.

# usage 
```shell
python3 comdirect_financialreport.py 
```
## config
the script depends on a `config.json` on its root directory in order to work properly. in order to use the comdirect api you need to register [here](https://www.comdirect.de/cms/kontakt-zugaenge-api.html).

```json
{
    "username": "comdirect_user_name",
    "password": "comdirect_user_pin",
    "client_id": "user_xxxxxxxxxxxxxxxxxxx",
    "client_secret": "comidrect_client_secret",
    "telegram": {
        "bot_token": "telegram_bot_token",
        "bot_chat_id": "telegram_chat_id"
    }
}
```

## dependencies
```sh
pip3 install python-dateutil
pip3 install matplotlib
```

## thanks
thanks [keisentraut](https://github.com/keisentraut/python-comdirect-api) for oauth implementation.


