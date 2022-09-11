import json

import pytz


def local_datetime(datetime_obj):
    utcdatetime = datetime_obj.replace(tzinfo=pytz.utc)
    tz = "Africa/Nairobi"
    return utcdatetime.astimezone(pytz.timezone(tz))


def add_token(token, db: set, file: str):
    if token not in db:
        db.add(token + "\n")

        with open(file, "r+") as f:
            f.seek(0)
            f.truncate(0)
            f.writelines(db)
            return f"Token **{token}** has been added to the list"

    return f"Token **{token}** already exists in the tokens list"


def show_tokens(db: set):
    if db:
        return db

    return "No tokens were registered"

def clear_tokens(db):
    with open(db, "w") as f:
        f.seek(0)
        f.truncate(0)

    return "Cleared {} tokens"

def _populate_leaderboard(new_data):
    with open("leaderboard.json", "r+", encoding="utf8") as board:
        lb = json.load(board)

        # load board and dict and update board
        # new_data is a dict
        if not lb:
            lb.update(new_data)
            sort_dict_based_on_values(lb)
            board.seek(0)
            json.dump(lb, board, indent=4, sort_keys=True)
            return f"Added {new_data} to board"

        for key in new_data:
            if key in lb.keys():
                lb[key] += new_data[key]
            else:
                lb[key] = new_data[key]

        sort_dict_based_on_values(lb)
        board.seek(0)
        json.dump(lb, board, indent=4, sort_keys=True)
        return f"Board updated with: {new_data}"


def sort_dict_based_on_values(dictionary: dict):
    sorted_dict = dict(sorted(dictionary.items(), key=lambda x: x[1], reverse=True))
    return sorted_dict
