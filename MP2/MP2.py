import pyodbc
import sys

def ConnectDatabase():
    connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=MP2;UID=SA;PWD=konoDI0da'
    connect = pyodbc.connect(connection_string, autocommit=False)
    cursor = connect.cursor()
    cursor.execute(  '''IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MP2') BEGIN 
                            CREATE DATABASE MP2 
                        END; 
                        USE MP2;
                        DROP TABLE IF EXISTS Course_registration;
                        DROP TABLE IF EXISTS Student;
                        DROP TABLE IF EXISTS Course;
                        CREATE TABLE Student (
                            ID int PRIMARY KEY,
                            Name VARCHAR(20),
                            Age INT,
                            Dept VARCHAR(20)
                        );
                        CREATE TABLE Course (
                            CourseID INT PRIMARY KEY,
                            CourseName VARCHAR(128),
                            Capacity INT,
                            RemainCapacity INT,
                            CreditHour INT,
                            Requirement xml,
                            CONSTRAINT RemainNotNegative
                                CHECK (RemainCapacity >= 0)
                        );
                        CREATE TABLE Course_registration (
                            StudentID INT FOREIGN KEY REFERENCES Student(ID) ON DELETE CASCADE,
                            CourseID INT FOREIGN KEY REFERENCES Course(CourseID) ON DELETE CASCADE,
                            Grade FLOAT
                        ); ''')
    cursor.execute(  '''CREATE TRIGGER Update_RemainCapacity_when_update_Capacity
                        ON Course
                        AFTER UPDATE 
                        AS
                        BEGIN
                            UPDATE Course SET RemainCapacity = (
                                SELECT Capacity - (
                                    SELECT COUNT(*) FROM Course_registration
                                    WHERE CourseID = INSERTED.CourseID
                                    AND Grade IS NULL
                                )
                                FROM Course WHERE CourseID = INSERTED.CourseID
                            )
                            FROM INSERTED
                            WHERE Course.CourseID = INSERTED.CourseID
                        END''')
    cursor.execute(  '''CREATE TRIGGER Update_RemainCapacity_when_modify_registration
                        ON Course_registration
                        AFTER INSERT, UPDATE, DELETE
                        AS
                        BEGIN
                            UPDATE Course SET RemainCapacity = RemainCapacity - 1
                            FROM INSERTED
                            WHERE Course.CourseID = INSERTED.CourseID
                            AND INSERTED.Grade IS NULL;
                            UPDATE Course SET RemainCapacity = RemainCapacity + 1
                            FROM DELETED
                            WHERE Course.CourseID = DELETED.CourseID
                            AND DELETED.Grade IS NULL;
                        END''')
    # Grading a student means that the student has completed the course, and hence does not take up capacity any more
    connect.commit()
    print('[Operation Log] Successfully connected to the database.')
    return connect, cursor

def CloseDatabaseConnection(connect):
    connect.close()
    print('[Operation Log] Successfully closed the database connection.')

def InsertStudent(ID, name, age, dept):
    print('[Operation Log] Inserting student (ID={}, Name={}, Age={}, Dept={})...'.format(ID, name, age, dept), end='')
    try:
        cursor.execute('INSERT INTO Student VALUES (?,?,?,?)', (ID, name, age, dept))
    except pyodbc.IntegrityError as err:
        print('Failed to insert: student\'s ID {} is used.'.format(ID))
        connect.rollback()
        return
    connect.commit()
    print('Successful.')

def InsertCourse(ID, name, capacity, credit_hour, requirement):
    print('[Operation Log] Inserting Course (ID={}, Name={}, Capacity={}, CreditHour={}, Requirement={})...'.format(ID, name, capacity, credit_hour, requirement), end='')
    try:
        cursor.execute('INSERT INTO Course VALUES (?,?,?,?,?,?)', (ID, name, capacity, capacity, credit_hour, requirement))
    except pyodbc.IntegrityError as err:
        if 'duplicate key' in str(err):
            print('Failed to insert: courseID {} is used.'.format(ID))
        else:
            print('Failed to insert: Unexpected integrity error: ' + str(err))
        connect.rollback()
    connect.commit()
    print('Successful.')

def DeleteStudent(ID):
    cursor.execute('DELETE FROM Student WHERE ID = ?', ID)
    connect.commit()
    print('[Operation Log] Successfully deleted student {}.'.format(ID))

def DeleteCourse(ID):
    cursor.execute('DELETE FROM Course WHERE CourseID = ?', ID)
    connect.commit()
    print('[Operation Log] Successfully deleted course {}.'.format(ID))

def EnrolledStudent(ID):
    cursor.execute('SELECT COUNT(*) FROM Course_registration WHERE CourseID = ? AND Grade IS NULL;', ID) # No grade means new students
    row = cursor.fetchone()
    connect.commit()
    return row[0]

def CheckRequirement(studentID, courseID):
    # Check prerequisite courses
    cursor.execute(  '''SELECT TOP 1 T.x.value('.', 'int') 
                        FROM Course 
                        CROSS APPLY Requirement.nodes('/Req/PrerequisiteCourse') T(x) 
                        WHERE CourseID = ? 
                        AND T.x.value('.', 'int') NOT IN (
                            SELECT CourseID 
                            FROM Course_registration WHERE StudentID = ? AND Grade >= 60
                        );''', courseID, studentID)
    row = cursor.fetchone()
    if(row):
        print("Failed to register: The student has not taken the prerequisite course {}.".format(row[0]))
        connect.rollback()
        return False
    # Check department
    cursor.execute("SELECT Dept FROM Student WHERE ID = ?", studentID) # execute this piece of sql independently for error message
    StudentDept = cursor.fetchone()[0] 
    cursor.execute(  '''SELECT TOP 1 T.x.value('.', 'VARCHAR(20)') 
                        FROM Course 
                        CROSS APPLY Requirement.nodes('/Req/Dept') T(x) 
                        WHERE CourseID = ? 
                        AND T.x.value('.', 'VARCHAR(20)') = ?''', courseID, StudentDept)
    # * FROM Course;) DROP TABLE Coourse; --
    if(not cursor.fetchone()):
        print("Failed to register: Students from department {} cannot take this course.".format(StudentDept))
        connect.rollback()
        return False
    return True

def RegisterCourse(studentID, courseID): # TODO: transaction
    print('[Operation Log] Registering student {} to course {}...'.format(studentID, courseID), end='')
    if(not CheckRequirement(studentID, courseID)):
        connect.rollback()
        return
    try:
        cursor.execute('INSERT INTO Course_registration VALUES(?,?,NULL);', (studentID, courseID))
    except pyodbc.IntegrityError as err:
        print('Failed to register: The course has no enough capacity.')
        connect.rollback()
        return
    connect.commit()
    print('Successful.')

def RemoveRegistration(studentID, courseID):
    cursor.execute('DELETE FROM Course_registration WHERE CourseID = ? AND StudentID = ?;', courseID, studentID)
    connect.commit()
    print('[Operation Log] Successfully deleted student {} from course {}.'.format(studentID, courseID))

def UpdateCapacity(courseID, new_capacity):
    print('[Operation Log] Updating capacity of course {} to {}...'.format(courseID, new_capacity), end='')
    try:
        cursor.execute('UPDATE Course SET Capacity = ? WHERE CourseID = ?;', new_capacity, courseID)
    except pyodbc.IntegrityError as err:
        print('Failed to update capacity: The new capacity is less than the number of students registered for this course.')
        connect.rollback()
        return
    connect.commit()
    print('Successful.')

def RetrieveAcademicHistory(studentID):
    cursor.execute("SELECT CourseID FROM Course_registration WHERE StudentID = ?", studentID)
    CourseList = []
    row = cursor.fetchone()
    while(row):
        CourseList.append(row[0])
        row = cursor.fetchone()
    connect.commit()
    return CourseList

def RetrieveFailureHistory():
    cursor.execute("SELECT StudentID, CourseID FROM Course_registration WHERE Grade < 60")
    StudentCourseList = []
    row = cursor.fetchone()
    while(row):
        StudentCourseList.append(row)
        row = cursor.fetchone()
    connect.commit()
    return StudentCourseList

def UpdateGrade(studentID, courseID, new_grade):
    cursor.execute("UPDATE Course_registration SET Grade = ? WHERE StudentID = ? AND CourseID = ?", new_grade, studentID, courseID)
    connect.commit()
    print("[Operation Log] Successfully updated student {}'s grade for course {} to {}.".format(studentID, courseID, new_grade))

def ComputeGPA(studentID): 
    cursor.execute(  '''SELECT SUM((
                            CASE
                            WHEN Grade >= 90 THEN 4.0
                            WHEN Grade >= 85 THEN 3.6
                            WHEN Grade >= 80 THEN 3.3
                            WHEN Grade >= 77 THEN 3.0
                            WHEN Grade >= 73 THEN 2.6
                            WHEN Grade >= 70 THEN 2.0
                            WHEN Grade >= 63 THEN 1.6
                            WHEN Grade >= 60 THEN 1.3
                            ELSE 0.0
                            END
                        )* Course.CreditHour) / SUM(Course.CreditHour) 
                        FROM Course_registration, Course 
                        WHERE StudentID = ? 
                        AND Course_registration.CourseID = Course.CourseID 
                        AND Course_registration.Grade IS NOT NULL''', studentID)
    ret = cursor.fetchone()[0]
    connect.commit()
    return ret

def ComputeAverageGrade(courseID):
    cursor.execute("SELECT AVG(Grade) FROM Course_registration WHERE CourseID = ?", courseID)
    ret = cursor.fetchone()[0]
    connect.commit()
    return ret

# Two functions for testing: PRintTable() & PrintAll
def PrintTable(TableName):
    print('--- Table "' + TableName + '" ---')
    cursor.execute("SELECT * FROM " + TableName)
    row = cursor.fetchone()
    while(row):
        print(row)
        row = cursor.fetchone()

def PrintAll():
    PrintTable('Student')
    PrintTable('Course')
    PrintTable('Course_registration')

# Begin Testing
print('''==== Test Stage 0 ====
  Functions to test: 
  - ConnectDatabase()
  - InsertStudent()
  - InsertCourse()
======================''')
connect, cursor = ConnectDatabase()

# Insert some students
InsertStudent(82, 'RabbitHu', 19, 'CS')
InsertStudent(83, 'GXZlegend', 18, 'AI')
InsertStudent(82, 'Xiaodi Yuan', 19, 'AI') # This student should NOT be inserted because ID 82 is already used.
InsertStudent(84, 'Han Wang', 19, 'AI')
PrintTable('Student') # Check if the students insertion is right

# Insert some courses.
InsertCourse(101, 'Machine Learning', 3, 4, '<Req><PrerequisiteCourse>105</PrerequisiteCourse><Dept>AI</Dept></Req>')
InsertCourse(102, 'Intro to CS', 2, 3, '<Req><Dept>CS</Dept><Dept>AI</Dept></Req>')
InsertCourse(103, 'Intro to AI', 2, 3, '<Req><Dept>AI</Dept><Dept>CS</Dept></Req>')
InsertCourse(104, 'C++', 3, 4, '<Req><PrerequisiteCourse>102</PrerequisiteCourse><Dept>CS</Dept><Dept>AI</Dept></Req>')
InsertCourse(105, 'Python', 3, 3, '<Req><Dept>AI</Dept><Dept>CS</Dept></Req>')
InsertCourse(106, 'Intro to DB', 3, 2, '''<Req>
    <PrerequisiteCourse>104</PrerequisiteCourse>
    <PrerequisiteCourse>105</PrerequisiteCourse>
    <Dept>CS</Dept>
    <Dept>AI</Dept>
    </Req>''')
InsertCourse(103, 'Roads to Academic', 320, 3, '') # This course should NOT be inserted because CourseID 103 is already used.
PrintTable('Course') # Check if the course insertion is right

# Test other functions
print('''\n==== Test Stage 1 ====
  Functions to test: 
  - RegisterCourse()
  - UpdateGrade()
  - RetrieveAcademicHistory()
  - RetrieveFailureHistory()
  - ComputeGPA()
======================''')
RegisterCourse(82, 102)
UpdateGrade(82, 102, 88)
RegisterCourse(82, 104)
UpdateGrade(82, 104, 95)
RegisterCourse(82, 105)

RegisterCourse(82, 106) # Should fail because student 82 has not passed course 105
UpdateGrade(82, 105, 92)
RegisterCourse(82, 106) # Should succeed this time
UpdateGrade(82, 106, 59)
RegisterCourse(82, 101) # Should fail because only AI students can register for course 101
print('Academic History of student 82: ' + str(RetrieveAcademicHistory(82)))
print('(StudentID, CourseID) pairs of failure records: ' + str(RetrieveFailureHistory()))
print('GPA of student 82: %.2f' % (ComputeGPA(82))) # Should get (3*3.6+7*4)/12 = 3.23
PrintAll() # Check all the tables

print('''\n==== Test Stage 2 ====
  Functions to test: 
  - RegisterCourse() (Capacity restriction)
  - ComputeAverageGrade()
======================''')
RegisterCourse(83, 102)
UpdateGrade(83, 102, 99)
print('Average grade of course 102: ' + str(ComputeAverageGrade(102))) # Should get (88+99)/2 = 93.5

RegisterCourse(83, 103)
RegisterCourse(82, 103)
RegisterCourse(84, 103) # Should fail because there's no capacity
print('Academic History of student 84: ' + str(RetrieveAcademicHistory(84))) # To check
PrintAll() # Check all the tables

print('''\n==== Test Stage 3 ====
  Functions to test: 
  - DeleteStudent()
  - EnrolledStudent()
  - DeleteCourse()
======================''')
PrintAll() # Before delete, there's a record about student 83
DeleteStudent(83)
PrintAll() # After delete, there's no records about student 83
RegisterCourse(84, 103) # Should succeed this time
UpdateCapacity(103, 1) # Should fail because 2 students (82 and 84) have registered for course 103
RemoveRegistration(84, 103)
UpdateCapacity(103, 1) # Should succeed this time
print("{} students have enrolled in course 102.".format(EnrolledStudent(103))) # Only 1 student (student 82)
DeleteCourse(102)
PrintAll()

print('''\n==== Test Stage 4 ====
  Functions to test: 
  - CloseDatabaseConnection
======================''')
CloseDatabaseConnection(connect)
