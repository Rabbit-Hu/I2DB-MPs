#include <sqlite3.h>
#include <stdio.h>

// init(): 
//     Connect to/Create a SQLite instance on a local file "MP1.db",
//     which contains a table with 4 columns (ID, Name, GPA, Age).
//     Return 1 when there is error.
//     NOTE: use the POINTER of db as parameter, since C parameters cannot be referenced, unlike C++...
int init(sqlite3 **p_db){
    int rc = sqlite3_open("MP1.db", p_db);
    if(rc != SQLITE_OK){
        fprintf(stderr, "Cannot open database: %s\n", sqlite3_errmsg(*p_db));
        return 1;
    }
    char *sql = "DROP TABLE IF EXISTS Students;"
                "CREATE TABLE Students(ID INT, Name CHAR(100), GPA DOUBLE, Age INT);";
    char *errmsg = 0;
    rc = sqlite3_exec(*p_db, sql, 0, 0, &errmsg);
    if(rc != SQLITE_OK){
        fprintf(stderr, "SQL Error: %s\n", sqlite3_errmsg(*p_db));
        sqlite3_free(errmsg);
        sqlite3_close(*p_db);
        return 1;
    }
    return 0;
}

// add_student(): Add a student to the table with given values.
int add_student(sqlite3 *db, int ID, char *Name, double GPA, int Age){
    char sql[200] = "";
    sprintf(sql, "INSERT INTO Students VALUES(%d, \"%s\", %lf, %d);", ID, Name, GPA, Age);
    //printf("%s\n", sql);
    char *errmsg = 0;
    int rc = sqlite3_exec(db, sql, 0, 0, &errmsg);
    if(rc != SQLITE_OK){
        fprintf(stderr, "SQL Error: %s\n", sqlite3_errmsg(db));
        sqlite3_free(errmsg);
        sqlite3_close(db);
        return 1;
    }
    return 0;
}

// remove_student(): Remove student with given ID.
int remove_student(sqlite3 *db, int ID){
    char sql[200] = "";
    sprintf(sql, "DELETE FROM Students WHERE ID = %d;", ID);
    char *errmsg = 0;
    int rc = sqlite3_exec(db, sql, 0, 0, &errmsg);
    if(rc != SQLITE_OK){
        fprintf(stderr, "SQL Error: %s\n", sqlite3_errmsg(db));
        sqlite3_free(errmsg);
        sqlite3_close(db);
        return 1;
    }
    return 0;
}

static int callback(void *NotUsed, int argc, char **argv, char **azColName){
    NotUsed = 0;
    for(int i = 0; i < argc; i++){
        printf("%s = %s\n", azColName[i], argv[i] ? argv[i]: "NULL");
    }
    printf("\n");
    return 0;
}

// select_all(): Print the whole table.
int select_all(sqlite3 *db){
    char *sql = "SELECT * FROM Students", *errmsg = 0;
    int rc = sqlite3_exec(db, sql, callback, 0, &errmsg);
    if(rc != SQLITE_OK){
        fprintf(stderr, "SQL Error: %s\n", sqlite3_errmsg(db));
        sqlite3_free(errmsg);
        sqlite3_close(db);
        return 1;
    }
    return 0;
}

// query_by_ID(): Print student with given ID.
int query_by_ID(sqlite3 *db, int ID){
    char sql[200] = "";
    sprintf(sql, "SELECT * FROM Students WHERE ID = %d;", ID);
    char *errmsg = 0;
    printf("Query result: \n\n");
    int rc = sqlite3_exec(db, sql, callback, 0, &errmsg);
    if(rc != SQLITE_OK){
        fprintf(stderr, "SQL Error: %s\n", sqlite3_errmsg(db));
        sqlite3_free(errmsg);
        sqlite3_close(db);
        return 1;
    }
    return 0;
}

int main(){

    sqlite3 *db;

    // Connect & Create table
    if(init(&db)) return 1;

    // Add students
    if(add_student(db, 2019012380, "GT", 3.9, 19)) return 1;
    if(add_student(db, 2019012382, "YXD", 1.3, 19)) return 1;
    if(add_student(db, 2019012383, "GXZ", 4.0, 18)) return 1;
    if(add_student(db, 2019012384, "WH", 3.0, 19)) return 1;
    select_all(db); // Print the whole table for test

    // Query by ID
    if(query_by_ID(db, 2019012382)) return 1; // Find YXD

    // Remove student
    if(remove_student(db, 2019012382)) return 1; // Remove YXD
    if(query_by_ID(db, 2019012382)) return 1; // Find YXD again, no record

    // Close the database instance
    sqlite3_close(db);

    return 0;
}