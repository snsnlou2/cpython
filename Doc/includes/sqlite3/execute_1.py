
import sqlite3
con = sqlite3.connect(':memory:')
cur = con.cursor()
cur.execute('create table people (name_last, age)')
who = 'Yeltsin'
age = 72
cur.execute('insert into people values (?, ?)', (who, age))
cur.execute('select * from people where name_last=:who and age=:age', {'who': who, 'age': age})
print(cur.fetchone())
con.close()
