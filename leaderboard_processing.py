import json


def _add_token(token, db):
    if token not in db.keys():
        db[token] = {}
        return f"Token **{token}** has been added to the list"
    else:
        return f"Token **{token}** already exists"


def _show_tokens(db):
    if db.keys():
        return list(db.keys())

    return "No tokens were registered"


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
