CREATE TABLE holdings (
    userId INTEGER NOT NULL REFERENCES users(id),
    symbol TEXT NOT NULL,
    amount DECIMAL(20,8) NOT NULL CHECK (amount >= 0),
    PRIMARY KEY (userId, symbol)
);
