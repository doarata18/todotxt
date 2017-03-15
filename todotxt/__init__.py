# -*- coding: utf-8 -*-
"""The main endpoint for todotxt."""

from datetime import datetime, date, timedelta
from operator import attrgetter
import re
import codecs

DATE_REGEX = "([\\d]{4})-([\\d]{2})-([\\d]{2})"
CONTEXT_REGEX = "\\s(@\\S+)"    # Unicode Contexts hit
PROJECT_REGEX = "\\s(\\+\\S+)"  # Unicode Projects hit
NO_PRIORITY_CHARACTER = "^"
DUEDATE_REGEX = "due\\:(\\S+)"
THRESHOLDDATE_REGEX = "t\\:(\\S+)"
RECURSIVE_REGEX = "rec\\:(\\S+)"
REC_SYNTAX_REGEX = "(\\+*)([0-9]+)([dwmyb])"

DUEDATE_SIG = "due:"
THRESHOLDDATE_SIG = "t:"
RECURSIVE_SIG = "rec:"

HOLIDAY_TBL = []    # type: List[str]  ##list of "YYYY-MM-DD" formated string


def date_value(arg_date):
    """
    Expand Date Value.
    In due_date(due:) and threshold_date(t:), specify some keywords available.
      - YYYY-MM-DD, YYYY/MM/DD
      - mon, tue, wed, thu, fri, sat, sun
      - monday, tuesday, wednesday, thursday, friday, saturday, sunday
      - today, tommorow, yesterday

      Args: arg_date / str or datetime.datetime or datetime.date

      Returns: datetime.datetime
    """
    _weekdays = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5,
                 "sun": 6, "monday": 0, "tuesday": 1, "wednesday": 2,
                 "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}

    _keywords = {"today": 0, "tomorrow": 1, "yesterday": -1}

    retval = None
    if isinstance(arg_date, date):  # datetime or date
        arg_date = arg_date.strftime("%Y-%m-%d")
    else:
        arg_date = arg_date.replace("/", "-")

    match = re.search(DATE_REGEX, arg_date)     # ISO-Format Date
    if match is not None:
        retval = datetime.strptime(match.group(0), "%Y-%m-%d")

    elif arg_date in _weekdays:
        today = datetime(*datetime.today().timetuple()[:3])
        wdtdy = today.weekday()
        wdtgt = _weekdays[arg_date]
        retval = today + timedelta(days=(wdtgt - wdtdy
                                         + (7 if wdtgt < wdtdy else 0)))

    elif arg_date in _keywords:
        retval = datetime(*datetime.today().timetuple()[:3]) \
                 + timedelta(days=_keywords[arg_date])

    return retval


def bizdate_add(start=None, addcnt=1):
    """add date in business date.
        Args:
            start(=datetime, default:today()): base date.
            addcnt(>=0, default:1): number of add days.

        Returns:
            added datetime (skip sat, sun and holiday)

        HOLIDAY_TBL<list> - \"YYYY-MM-DD\" formated str list, deal holiday.
            default []
    """
    if start is None:
        start = datetime(*datetime.today().timetuple()[:3])

    retv = start
    for i in range(addcnt):
        retv += timedelta(days=1)
        while retv.weekday() >= 5 \
            or (retv.strftime("%Y-%m-%d") in HOLIDAY_TBL):
            # sat~sun, holiday
            retv += timedelta(days=1)
    return retv


class Task(object):
    """A class that represents a task."""

    def __init__(self, raw_todo="[dummy task]", tid=-1):

        self.tid = tid
        self.raw_todo = raw_todo
        self.priority = NO_PRIORITY_CHARACTER
        self.todo = ""
        self.projects = []
        self.contexts = []
        self.finished = False
        self.created_date = None
        self.finished_date = None
        self.threshold_date = None
        self.due_date = None
        self.recursive = None

        self.parse()

    def __str__(self):
        return "{0}: {1}".format(self.tid, self.raw_todo)

    def __repr__(self):
        return "<Task {0} '{1}'>".format(self.tid, self.raw_todo)

    def __eq__(self, other):
        return self.raw_todo == other.raw_todo

    def __ne__(self, other):
        return not self.__eq__(other)

    def parse(self):
        """Parse the text of self.raw_todo and update internal state."""

        rebuild_flg = False
        text = self.raw_todo
        splits = text.split(" ")
        if text[0] == "x" and text[1] == " ":
            self.finished = True
            splits = splits[1:]

            match = re.search(DATE_REGEX, splits[0])
            if match is not None:
                self.finished_date = \
                    datetime.strptime(match.group(0), "%Y-%m-%d")
                splits = splits[1:]
        else:
            self.finished = False
            self.finished_date = None

        head = splits[0]

        if (len(head) == 3) and \
                (head[0] == "(") and \
                (head[2] == ")") and \
                (ord(head[1]) >= 65 and ord(head[1]) <= 90):

            self.priority = head[1]
            splits = splits[1:]
        else:
            self.priority = NO_PRIORITY_CHARACTER

        match = re.search(DATE_REGEX, splits[0])
        if match is not None:
            self.created_date = datetime.strptime(match.group(0), "%Y-%m-%d")
            splits = splits[1:]

        # threshold date getting
        match = [x for x in splits if x.startswith(THRESHOLDDATE_SIG)]
        if len(match) != 0:
            self.threshold_date = \
                date_value(match[0][len(THRESHOLDDATE_SIG):])
            # strip "t:" node from splits
            for i in match:
                splits.remove(i)
            rebuild_flg = True

        # due-date getting
        match = [x for x in splits if x.startswith(DUEDATE_SIG)]
        if len(match) != 0:
            self.due_date = \
                date_value(match[0][len(DUEDATE_SIG):])
            # strip "due:" node from splits
            for i in match:
                splits.remove(i)
            rebuild_flg = True

        # rec: extension getting
        match = [x for x in splits if x.startswith(RECURSIVE_SIG)]
        if len(match) != 0:
            self.recursive = match[0].lstrip(RECURSIVE_SIG)
            # strip "rec:" node from splits
            for i in match:
                splits.remove(i)

        # match = [x for x in splits if x[0] == "@"]
        match = re.findall(CONTEXT_REGEX, " ".join(splits))
        if len(match) != 0:
            self.contexts = match

        for i in [x for x in splits if x.startswith("@")]:
            splits.remove(i)

        # match = [x for x in splits if x[0] == "+"]
        match = re.findall(PROJECT_REGEX, " ".join(splits))
        if len(match) != 0:
            self.projects = match

        for i in [x for x in splits if x.startswith("+")]:
            splits.remove(i)

        self.todo = " ".join(splits).strip()

        if rebuild_flg:
            # There is a possibility that date expansion occurred
            # during the date_value() call.
            self.rebuild_raw_todo()

    def matches(self, text):
        """Determines whether the tasks matches the text.

        Args:
            text: the text to be matched

        Returns:
            Either True or False.
        """

        return text in self.raw_todo

    def rebuild_raw_todo(self):
        """Rebuilds self.raw_todo from data associated with the Task object.

        Returns:
            The rebuilt self.raw_todo.
        """

        finished = "x " if self.finished else ""
        created_date = self.created_date.strftime("%Y-%m-%d ") if \
            self.created_date is not None else ""

        finished_date = self.finished_date.strftime("%Y-%m-%d ") if \
            self.finished and self.finished_date is not None else ""

        priority = "(" + self.priority + ") " if \
            self.priority != NO_PRIORITY_CHARACTER else ""

        threshold = THRESHOLDDATE_SIG \
            + date_value(self.threshold_date).strftime("%Y-%m-%d") if \
                self.threshold_date is not None else ""

        due = DUEDATE_SIG \
            + date_value(self.due_date).strftime("%Y-%m-%d") if \
                self.due_date is not None else ""

        recursive = RECURSIVE_SIG + self.recursive if \
            self.recursive is not None else ""

        self.raw_todo = u"{0}{1}{2}{3}{4}{5}{6}{7}{8}{9}" \
            .format(finished,
                    finished_date if self.finished else "",
                    priority,
                    created_date,
                    self.todo,
                    (" " + " ".join(self.projects)) if self.projects else "",
                    (" " + " ".join(self.contexts)) if self.contexts else "",
                    (" " + threshold) if threshold else "",
                    (" " + due) if due else "",
                    (" " + recursive) if recursive else "").strip()

        return self.raw_todo


class Tasks(object):

    """Task manager that handles loading, saving and filtering tasks."""

    # the location of the todo.txt file
    path = None             # type: str
    archive_path = None     # type: str
    tasks = []              # type: List[Task]
    archives = []           # type: List[Task]

    # the dict that holds event handlers
    handlers = {}           # type: Dict[str, function]

    def __init__(self, path=None, archive_path=None, tasks=None):
        self.path = path
        self.archive_path = archive_path
        self.tasks = tasks if tasks is not None else []
        self.archives = []

    def __str__(self):
        return str(self.tasks)

    def __repr__(self):
        return "<Tasks {0}>".format(self.__str__())

    def __iter__(self):
        return iter(self.tasks)

    def __len__(self):
        return len(self.tasks)

    def __getitem__(self, key):
        return self.tasks[key]

    def __setitem__(self, key, value):
        if isinstance(value, str):
            self.tasks[key] = Task(value)
        elif isinstance(value, Task):
            self.tasks[key] = value

    def __delitem__(self, key):
        del self.tasks[key]

    def _trigger_event(self, event):
        """Triggers an event by calling handler functions assigned for it.

        Args:
            event -- the event to trigger"""

        if event in self.handlers:
            for handler in self.handlers[event]:
                handler(self)

    def load(self, filename=None):
        """Loads tasks from given file, parses them into internal
        representation and stores them in this manager's object.
            Args:
                filename : load-filename, default : self.path

            Returns:
                load success - True / load cancel - False
        """

        retval = False
        self._trigger_event("load")

        filename = self.path if filename is None else filename

        if filename:    # self.path set.
            with codecs.open(filename, "r", "utf-8") as f:
                i = len(self.tasks)
                for line in f:
                    if len(line.strip(" \t\n")) > 0:    # skip empty line
                        self.tasks.append(Task(line.strip(), i))
                        i += 1

            self._trigger_event("loaded")
            retval = True
        return retval

    def save(self, filename=None, archive_file=None):
        """Saves tasks that are saved in this manager. If specified they will
        be saved in the filename arguemnt of this function. Otherwise the
        default path (self.path) will be used.

        Args:
            filename -- An optional name of the file to save the tasklist into.
            archive_file -- An optional name of the file to save the archived.

        Returns:
            save success - True / save cancel - False
        """

        retval = False
        self._trigger_event("save")

        filename = self.path if filename is None else filename

        if filename:    # self.path set.
            with codecs.open(filename, "w", "utf-8") as f:
                for task in self.tasks:
                    f.write("{0}\n".format(task.rebuild_raw_todo()))

            archive_file = self.archive_path \
                if archive_file is None else archive_file

            if archive_file is not None and len(self.archives) > 0:
                with codecs.open(archive_file, "a", "utf-8") as f:
                    for arch in self.archives:
                        f.write("{0}\n".format(arch.rebuild_raw_todo()))
                self.archives = []

            self._trigger_event("saved")
            retval = True
        return retval

    def filter_by(self, text):
        """Filteres the tasks by a given filter text. Returns a new Tasks
        object. Note: the path parameter of the new object will stay the same.

        Args:
            text -- the text to filter the tasklist by

        Returns:
            A new :class:`Tasks` object that contains tasks that match the
            text.
        """

        return Tasks(self.path, self.archive_path,
                     filter(lambda x: x.matches(text), self.tasks))

    def order_by(self, criteria):
        """Sorts the tasks by given criteria and returns a new Tasks object
        with the new ordering. The criteria argument can have the following
        values:
            - tid
            - priority
            - finished
            - created_date
            - finished_date
            - due_date
            - threshold_date
        """

        reversed_ = False
        if criteria[0] == "-":
            reversed_ = True

        criterias = ["tid", "priority", "finished", "created_date",
                     "finished_date", "due_date", "threshold_date"]

        if criteria in criterias:
            return Tasks(self.path,
                         self.archive_path,
                         sorted(self.tasks, key=attrgetter(criteria),
                                reverse=reversed_))
        else:
            return self

    def add(self, text):
        """Adds a new task given the text.

        Args:
            text -- the text of the task

        Returns:
            A new :class:`Tasks` object that contains the newly created task"""

        self.tasks.append(Task(text, len(self.tasks)))
        return self

    def add_handler(self, event, handler):
        """Attach a handler function to an event.

        Args:
            event -- name of the event to attach the handler to
            handler -- the function that shall handle the event"""

        if event in self.handlers:
            self.handlers[event].append(handler)
        else:
            self.handlers[event] = [handler]

    def append(self, value="[dummy task]"):
        """Append to Tasks.tasks collection.

        Args:
            value(='[dummy task]'): text/Task/Tasks/list<text/Task/Tasks>)
        """
        if isinstance(value, Task):
            self.tasks.append(value)

        elif isinstance(value, str):
            self.add(value)

        elif isinstance(value, Tasks):
            self.tasks.extend(value.tasks)

        elif isinstance(value, list):
            for i in value:
                if isinstance(i, Task):
                    self.tasks.append(i)

                elif isinstance(i, str):
                    self.add(i)

                elif isinstance(i, Tasks):
                    self.tasks.extend(i.tasks)

    def archive(self):
        """archive finished tasks.

            Returns: archive tasks list.
        """
        finished = [x for x in self.tasks if x.finished]
        self.archives = self.archives + finished
        self.tasks = [x for x in self.tasks if not x.finished]
        return finished

    def create_recursive_tasks(self):
        """Create recursive tasks from finished tasks.
            rec syntax: \"rec:\"+*[0-9]+[dwmyb]
            \"b\" : business date (skip sat, sun and holiday)

            HOLIDAY_TBL<list> - \"YYYY-MM-DD\" formated str list, deal holiday.
                default []

            Returns: create tasks list.
        """
        _end_of_month = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                         7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
        createlist = []
        for i in [x for x in self.tasks if
                  x.finished and x.recursive is not None]:
            new_task = Task(i.raw_todo)
            new_task.finished = False
            new_task.finished_date = None
            new_task.threshold_date = None

            if i.due_date is not None:
                match = re.search(REC_SYNTAX_REGEX, i.recursive)
                rec_base = match.group(1)
                rec_span = int(match.group(2))
                rec_unit = match.group(3)

                if rec_base == "+":
                    base_date = i.due_date
                else:
                    base_date = i.finished_date if \
                                    i.finished_date is not None else \
                                    datetime(*datetime.today().timetuple()[:3])

                if rec_unit == "d":
                    new_due = base_date + timedelta(days=rec_span)

                elif rec_unit == "w":
                    new_due = base_date + timedelta(days=(rec_span * 7))

                elif rec_unit == "m":
                    rec_year = base_date.year \
                             + ((base_date.month + rec_span) // 12)
                    rec_month = (base_date.month + rec_span) % 12

                    if base_date.day > _end_of_month[rec_month]:
                        rec_day = _end_of_month[rec_month]
                        new_due = datetime(rec_year, rec_month, rec_day)
                        new_due += timedelta(days=(base_date.day - rec_day))
                    else:
                        new_due = datetime(rec_year, rec_month, base_date.day)

                elif rec_unit == "y":
                    if base_date.month == 2:
                        new_due = datetime(base_date.year + rec_span,
                                           base_date.month,
                                           1)
                        new_due += timedelta(days=(base_date.day - 1))
                    else:
                        new_due = datetime(base_date.year + rec_span,
                                           base_date.month,
                                           base_date.day)

                elif rec_unit == "b":
                    new_due = bizdate_add(base_date, rec_span)

                else:
                    new_due = base_date

                new_task.due_date = new_due

            new_task.rebuild_raw_todo()
            self.tasks.append(new_task)
            createlist.append(new_task)
        return createlist

    def get_projects(self):
        """Get projects in tasks collection."""
        s = set()
        for i in self.tasks:
            for j in i.projects:
                s.add(j)
        return sorted(list(s))

    def get_contexts(self):
        """Get contexts in tasks collection."""
        s = set()
        for i in self.tasks:
            for j in i.contexts:
                s.add(j)
        return sorted(list(s))

    def sort(self):
        """Tasks order sort by tid."""
        self.tasks = sorted(self.tasks, key=attrgetter("tid"))

    def renum(self, start=0, step=1):
        """Renumber tasks tids."""
        gen_tid = \
            (x for x in range(start, len(self.tasks) * step + start, step))
        self.sort()
        for i in self.tasks:
            i.tid = next(gen_tid)

    def reload(self):
        """Crear TasksList/ArchiveList and Loads tasks from given file."""
        self.tasks = []
        self.archives = []
        return self.load()
