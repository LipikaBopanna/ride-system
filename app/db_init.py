from app.common.db import Base, engine

def init_db():
    print("Creating DB schema... (this should be run once)")
    Base.metadata.create_all(bind=engine)
    print("Done.")

if __name__ == "__main__":
    init_db()
