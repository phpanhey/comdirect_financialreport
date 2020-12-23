import os
import requests
import uuid
import json
import datetime
import calendar
from dateutil.relativedelta import relativedelta
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import subprocess
import time


def get_credentials(credential_name):
    return json.loads(open("config.json", "r").read())[credential_name]


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S%f")


def callback_tan_push():
    #user has 30 seconds to confirm push tan.
    time.sleep(30)    


def authenticate_api():
    # thanks to keisentraut, oauth procedure copied from https://github.com/keisentraut/python-comdirect-api
    client_id = get_credentials("client_id")
    client_secret = get_credentials("client_secret")
    username = get_credentials("username")
    password = get_credentials("password")

    # POST /oauth/token
    response = requests.post(
        "https://api.comdirect.de/oauth/token",
        f"client_id={client_id}&"
        f"client_secret={client_secret}&"
        f"username={username}&"
        f"password={password}&"
        f"grant_type=password",
        allow_redirects=False,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    if not response.status_code == 200:
        raise RuntimeError(
            f"POST https://api.comdirect.de/oauth/token returned status {response.status_code}"
        )
    tmp = response.json()
    access_token = tmp["access_token"]
    refresh_token = tmp["refresh_token"]

    # GET /session/clients/user/v1/sessions
    session_id = uuid.uuid4()
    response = requests.get(
        "https://api.comdirect.de/api/session/clients/user/v1/sessions",
        allow_redirects=False,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "x-http-request-info": f'{{"clientRequestId":{{"sessionId":"{session_id}",'
            f'"requestId":"{timestamp()}"}}}}',
        },
    )
    if not response.status_code == 200:
        raise RuntimeError(
            f"GET https://api.comdirect.de/api/session/clients/user/v1/sessions"
            f"returned status {response.status_code}"
        )
    tmp = response.json()
    session_id = tmp[0]["identifier"]

    # POST /session/clients/user/v1/sessions/{sessionId}/validate
    response = requests.post(
        f"https://api.comdirect.de/api/session/clients/user/v1/sessions/{session_id}/validate",
        allow_redirects=False,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "x-http-request-info": f'{{"clientRequestId":{{"sessionId":"{session_id}",'
            f'"requestId":"{timestamp()}"}}}}',
            "Content-Type": "application/json",
        },
        data=f'{{"identifier":"{session_id}","sessionTanActive":true,"activated2FA":true}}',
    )
    if response.status_code != 201:
        raise RuntimeError(
            f"POST /session/clients/user/v1/sessions/.../validate returned status code {response.status_code}"
        )
    tmp = json.loads(response.headers["x-once-authentication-info"])
    challenge_id = tmp["id"]
    tan = callback_tan_push()

    # PATCH /session/clients/user/v1/sessions/{sessionId}
    response = requests.patch(
        f"https://api.comdirect.de/api/session/clients/user/v1/sessions/{session_id}",
        allow_redirects=False,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "x-http-request-info": f'{{"clientRequestId":{{"sessionId":"{session_id}",'
            f'"requestId":"{timestamp()}"}}}}',
            "Content-Type": "application/json",
            "x-once-authentication-info": f'{{"id":"{challenge_id}"}}',
            "x-once-authentication": tan,
        },
        data=f'{{"identifier":"{session_id}","sessionTanActive":true,"activated2FA":true}}',
    )
    tmp = response.json()
    if not response.status_code == 200:
        raise RuntimeError(
            f"PATCH https://api.comdirect.de/session/clients/user/v1/sessions/...:"
            f"returned status {response.status_code}"
        )
    session_id = tmp["identifier"]

    # POST https://api.comdirect.de/oauth/token
    response = requests.post(
        "https://api.comdirect.de/oauth/token",
        allow_redirects=False,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=f"client_id={client_id}&client_secret={client_secret}&"
        f"grant_type=cd_secondary&token={access_token}",
    )
    if not response.status_code == 200:
        raise RuntimeError(
            f"POST https://api.comdirect.de/oauth/token returned status {response.status_code}"
        )
    tmp = response.json()
    access_token = tmp["access_token"]
    refresh_token = tmp["refresh_token"]
    account_id = get_accountId({"access_token": access_token, "session_id": session_id})

    return {
        "access_token": access_token,
        "session_id": session_id,
        "refresh_token": refresh_token,
        "account_id": account_id,
    }


def get_authorized(access_credentials, url, extraheaders={}):
    access_token = access_credentials["access_token"]
    session_id = access_credentials["session_id"]
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "x-http-request-info": f'{{"clientRequestId":{{"sessionId":"{session_id}",'
        f'"requestId":"{timestamp()}"}}}}',
    }
    headers.update(extraheaders)
    response = requests.get(url, allow_redirects=False, headers=headers)
    if response.status_code != 200:
        raise RuntimeError(f"{url} returned HTTP status {response.status_code}")
    return response


def get_accountId(access_credentials):
    results = get_authorized(
        access_credentials,
        f"https://api.comdirect.de/api/banking/clients/user/v1/accounts/balances",
    )
    accounts = results.json()["values"]
    for account in accounts:
        if account["account"]["accountType"]["text"] == "Girokonto":
            return account["account"]["accountId"]


def get_transactions(access_credentials, start_date, end_date):
    account_id = access_credentials["account_id"]
    res = []

    while start_date <= end_date:
        start_date_str = start_date.strftime("%Y-%m-%d")
        res = (
            res
            + get_authorized(
                access_credentials,
                f"https://api.comdirect.de/api/banking/v1/accounts/{account_id}/transactions?min-bookingDate={start_date_str}&max-bookingDate={start_date_str}&transactionState=BOOKED",
            ).json()["values"]
        )
        start_date += datetime.timedelta(days=1)

    return res


def get_date_object(german_date_string):
    return datetime.date(
        int(german_date_string.split(".")[2]),
        int(german_date_string.split(".")[1]),
        int(german_date_string.split(".")[0]),
    )


def calculate_spend_money(transactions):
    sum = float(0.0)
    for transaction in transactions:
        val = float(transaction["amount"]["value"])
        if val < 0:
            sum += abs(val)

    return round(sum, 2)


def calculate_earned_money(transactions):
    sum = float(0.0)
    for transaction in transactions:
        val = float(transaction["amount"]["value"])
        if val > 0 and transaction["bookingStatus"] == "BOOKED":
            sum += val

    return round(sum, 2)


def get_month_transactions(access_credentials, date_obj):
    year = int(datetime.datetime.now(datetime.timezone.utc).strftime("%Y"))
    last_day = calendar.monthrange(year, date_obj.month)[1]

    return get_transactions(
        access_credentials,
        get_date_object(f"01.{date_obj.month}.{year}"),
        get_date_object(f"{last_day}.{date_obj.month}.{year}"),
    )


def calculate_finance_report_data(access_credentials):
    stamp = datetime.datetime.now()
    res = []
    for x in range(5):
        transactions = get_month_transactions(access_credentials, stamp)
        earned_money = calculate_earned_money(transactions)
        spend_money = calculate_spend_money(transactions)
        saldo = round(earned_money - spend_money, 2)

        res.insert(
            0,
            {
                "month": stamp.strftime("%b"),
                "earned_money": earned_money,
                "spend_money": spend_money,
                "saldo": saldo,
            },
        )

        stamp -= relativedelta(months=+1)

    return res


def autolabel(rects, ax):
    """Attach a text label above each bar in *rects*, displaying its height."""
    for rect in rects:
        height = rect.get_height()
        ax.annotate(
            "{}".format(height),
            xy=(rect.get_x() + rect.get_width() / 2, height),
            xytext=(0, 3),  # 3 points vertical offset
            textcoords="offset points",
            ha="center",
            va="bottom",
        )


def get_fields(finance_data, field_name):
    res = []
    for finance_data_item in finance_data:
        res.append(finance_data_item[field_name])
    return res


def create_graph(finance_data):
    chart_name = "chart.png"
    months = get_fields(finance_data, "month")
    earned_money = get_fields(finance_data, "earned_money")
    spend_money = get_fields(finance_data, "spend_money")

    x = np.arange(len(months))  # the label locations
    width = 0.35  # the width of the bars

    fig, ax = plt.subplots()
    rects1 = ax.bar(x - width / 2, earned_money, width, label="Einnahmen")
    rects2 = ax.bar(x + width / 2, spend_money, width, label="Ausgaben")

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel("geld in €")
    ax.set_title("einnahmen / ausgaben der letzten monate")
    ax.set_xticks(x)
    ax.set_xticklabels(months)
    ax.legend()
    autolabel(rects1, ax)
    autolabel(rects2, ax)
    fig.tight_layout()
    # plt.show()
    matplotlib.axes.Axes.bar
    matplotlib.pyplot.bar
    matplotlib.axes.Axes.annotate
    matplotlib.pyplot.annotate
    plt.savefig(chart_name)
    return chart_name


def telegram_bot_send_text(bot_message):
    bot_token = get_credentials("telegram")["bot_token"]
    bot_chatID = get_credentials("telegram")["bot_chat_id"]
    send_text = (
        "https://api.telegram.org/bot"
        + bot_token
        + "/sendMessage?chat_id="
        + bot_chatID
        + "&parse_mode=Markdown&text="
        + bot_message
    )
    response = requests.get(send_text)
    return response.json()


def telegram_bot_send_image(image_name):
    command = (
        "curl -s -X POST https://api.telegram.org/bot"
        + get_credentials("telegram")["bot_token"]
        + "/sendPhoto -F chat_id="
        + get_credentials("telegram")["bot_chat_id"]
        + " -F photo=@"
        + image_name
    )
    subprocess.call(
        command.split(" "), stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL
    )
    return


def current_month_report(finance_data):
    current_month = finance_data[-1]
    return (
        "📅 "
        + current_month["month"]
        + "\n\n💸 Einnahmen: "
        + str(current_month["earned_money"])
        + " €\n💩 Ausgaben: "
        + str(current_month["spend_money"])
        + " €\n🥴 Saldo: "
        + str(current_month["saldo"])
        + " €"
    )

def delete_chart_image(chart_name):
    os.remove(chart_name)


access_credentials = authenticate_api()
finance_data = calculate_finance_report_data(access_credentials)
chart_name = create_graph(finance_data)
telegram_bot_send_text(current_month_report(finance_data))
telegram_bot_send_image(chart_name)
delete_chart_image(chart_name)