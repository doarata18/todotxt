# -*- coding: utf-8 -*-
"""The main endpoint for todotxt."""

from datetime import datetime
from operator import attrgetter
from copy import deepcopy
import re
import codecs

DATE_REGEX = "([\\d]{4})-([\\d]{2})-([\\d]{2})"
##CONTEXT_REGEX = '(@\\w+)'
##PROJECT_REGEX = '(\\+\\w+)'
CONTEXT_REGEX = '\s(@\\S+)'   # Unicode Contexts hit
PROJECT_REGEX = '\s(\\+\\S+)' # Unicode Projects hit
NO_PRIORITY_CHARACTER = '^'
DUEDATE_REGEX = "due\\:(\\S+)"
THRESHOLDDATE_REGEX = "t\\:(\\S+)"
RECURSIVE_REGEX = "rec\\:(\\S+)"

DUEDATE_SIG = "due:"
THRESHOLDDATE_SIG = "t:"
RECURSIVE_SIG = "rec:"

class Task(object):

    """A class that represents a task."""
    tid = None
    raw_todo = ''
    priority = NO_PRIORITY_CHARACTER
    todo = ''
    projects = []
    contexts = []
    finished = False
    created_date = None
    finished_date = None
    threshold_date = None
    due_date = None
    recursive = None

    def __init__(self, raw_todo, id=-1):

        self.tid = id
        self.raw_todo = raw_todo

        self.parse()

    def parse(self):
        """Parse the text of self.raw_todo and update internal state."""

        text = self.raw_todo
        splits = text.split(' ')
        if text[0] == 'x' and text[1] == ' ':
            self.finished = True
            splits = splits[1:]

        match = re.search(DATE_REGEX, splits[0])
        if match is not None:
            self.finished_date = datetime.strptime(match.group(0), "%Y-%m-%d")
            splits = splits[1:]

        head = splits[0]

        if (len(head) == 3) and \
                (head[0] == '(') and \
                (head[2] == ')') and \
                (ord(head[1]) >= 65 and ord(head[1]) <= 90):

            self.priority = head[1]
            splits = splits[1:]

        match = re.search(DATE_REGEX, splits[0])
        if match is not None:
            self.created_date = datetime.strptime(match.group(0), "%Y-%m-%d")
            splits = splits[1:]

        # threshold date getting
        match = [x for x in splits if x.startswith(THRESHOLDDATE_SIG)]
        if len(match) != 0:
            # keyword(today, mon, monday, +[0-9]+[dwmyb])解析入れるなら、ここ
            # 日付書式エラー時の処理も必要
            self.threshold_date = \
                datetime.strptime(
                    match[0].lstrip(THRESHOLDDATE_SIG), "%Y-%m-%d")
            # splitsから"t:"節を取り除く処理
            for i in match:
                splits.remove(i)

        # due-date getting
        match = [x for x in splits if x.startswith(DUEDATE_SIG)]
        if len(match) != 0:
            # keyword(today, mon, monday, +[0-9]+[dwmyb])解析入れるなら、ここ
            # 日付書式エラー時の処理も必要
            self.due_date = \
                datetime.strptime(match[0].lstrip(DUEDATE_SIG), "%Y-%m-%d")
            # splitsから"due:"節を取り除く処理
            for i in match:
                splits.remove(i)

        # rec: extension getting
        match = [x for x in splits if x.startswith(RECURSIVE_SIG)]
        if len(match) != 0:
            self.recursive = match[0].lstrip(RECURSIVE_SIG)
            # splitsから"rec:"節を取り除く処理
            for i in match:
                splits.remove(i)

        self.todo = ' '.join(splits)

        ## match = [x for x in splits if x[0] == "@"]
        match = re.findall(CONTEXT_REGEX, self.todo)
        if len(match) != 0:
            self.contexts = match

        ## match = [x for x in splits if x[0] == "+"]
        match = re.findall(PROJECT_REGEX, self.todo)
        if len(match) != 0:
            self.projects = match

    def matches(self, text):
        """Determines whether the tasks matches the text.

        Args:
            text: the text to be matched

        Returns:
            Either True or False.
        """

        return text in self.todo

    def rebuild_raw_todo(self):
        """Rebuilds self.raw_todo from data associated with the Task object.

        Returns:
            The rebuilt self.raw_todo.
        """

        finished = 'x ' if self.finished else ''
        created_date = self.created_date.strftime("%Y-%m-%d ") if \
            self.created_date is not None else ''

        finished_date = self.finished_date.strftime("%Y-%m-%d ") if \
            self.finished_date is not None else ''

        priority = '(' + self.priority + ') ' if \
            self.priority != NO_PRIORITY_CHARACTER else ''

        due = DUEDATE_SIG + self.due_date.strftime("%Y-%m-%d ") if \
            self.due_date is not None else ""
        
        threshold = THRESHOLDDATE_SIG \
                         + self.threshold_date.strftime("%Y-%m-%d ") if \
            self.threshold_date is not None else ""

        recursive = RECURSIVE_SIG + self.recursive if \
            self.recursive is not None else ""

        self.raw_todo = \
            "{0}{1}{2}{3}{4}{5}{6}{7}".format(finished,
                                              finished_date,
                                              priority,
                                              created_date,
                                              self.todo + " ",
                                              threshold,
                                              due,
                                              recursive)

        return self.raw_todo

    def __str__(self):
        return "{0}: {1}".format(self.tid, self.raw_todo)

    def __repr__(self):
        return "<Task {0} '{1}'>".format(self.tid, self.raw_todo)

    ## customize metods
    def __eq__(self, other):
        return True if self.raw_todo == other.raw_todo else False

    def __ne__(self, other):
        return True if self.raw_todo != other.raw_todo else False

class Tasks(object):

    """Task manager that handles loading, saving and filtering tasks."""

    # the location of the todo.txt file
    path = ''
    tasks = []

    # the dict that holds event handlers
    handlers = {}

    def __init__(self, path=None, tasks=None):
        self.path = path
        self.tasks = tasks if tasks is not None else []

    def load(self):
        """Loads tasks from given file, parses them into internal
        representation and stores them in this manager's object."""

        self._trigger_event('load')

        with codecs.open(self.path, 'r', 'utf-8') as f:
            i = 0
            for line in f:
                self.tasks.append(Task(line.strip(), i))
                i += 1

        self._trigger_event('loaded')

    def save(self, filename=None):
        """Saves tasks that are saved in this manager. If specified they will
        be saved in the filename arguemnt of this function. Otherwise the
        default path (self.path) will be used.

        Args:
            filename -- An optional name of the file to save the tasklist into.
        """

        self._trigger_event('save')

        filename = self.path if filename is None else filename
        with codecs.open(filename, 'w', 'utf-8') as f:
            for task in self.tasks:
                f.write("{0}\n".format(task.rebuild_raw_todo()))

        self._trigger_event('saved')

    def filter_by(self, text):
        """Filteres the tasks by a given filter text. Returns a new Tasks
        object. Note: the path parameter of the new object will stay the same.

        Args:
            text -- the text to filter the tasklist by

        Returns:
            A new :class:`Tasks` object that contains tasks that match the
            text.
        """

        return Tasks(self.path, filter(lambda x: x.matches(text), self.tasks))

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

        reversed = False
        if criteria[0] == '-':
            reversed = True

        criterias = ['tid', 'priority', 'finished', 'created_date',
                     'finished_date', 'due_date', 'threshold_date']

        if criteria in criterias:
            return Tasks(self.path,
                         sorted(self.tasks, key=attrgetter(criteria),
                                reverse=reversed))
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

    def _trigger_event(self, event):
        """Triggers an event by calling handler functions assigned for it.

        Args:
            event -- the event to trigger"""

        if event in self.handlers:
            for handler in self.handlers[event]:
                handler(self)

    def add_handler(self, event, handler):
        """Attach a handler function to an event.

        Args:
            event -- name of the event to attach the handler to
            handler -- the function that shall handle the event"""

        if event in self.handlers:
            self.handlers[event].append(handler)
        else:
            self.handlers[event] = [handler]

    def __str__(self):
        return str(self.tasks)

    def __repr__(self):
        return "<Tasks {0}>".format(self.__str__())

    ## customize methods
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

    def append(self, value="[dummy task]"):
        """Append to Tasks.tasks collection.

        Args:
            value(="[dummy task]"): text or Task object(=deepcopy(obj))
        """
        if isinstance(value, Task):
            self.tasks.append(deepcopy(value))
        else:
            self.add(value)

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
