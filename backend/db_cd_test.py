from backend.db import DB, Cooldown


def main():
    db = DB(save_every=0)
    cd = Cooldown(db, 'foo', 2)
    while True:
        if input("Set?"):
            cd.do()
        can = "yes" if cd.can_do() else "no"
        print(f"Can? {can}!")


if __name__ == "__main__":
    main()
