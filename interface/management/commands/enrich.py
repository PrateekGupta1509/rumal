#!/usr/bin/env python
#
# enrich.py
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA  02111-1307  USA
#
# Author:   Tarun Kumar <reach.tarun.here@gmail.com>
# NOTE: THIS IS AN INITIAL RELEASE AND IS LIKELY TO BE UNSTABLE

import logging
import os
import time
import requests

from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from interface.models import *
from interface.api import TaskResource
from interface.plug import PluginBase

import pymongo
import gridfs
from bson import ObjectId
from bson.json_util import loads, dumps

from interface.plugins import *

STATUS_NEW              = 0
STATUS_PROCESSING       = 1
STATUS_FAILED           = 2
STATUS_COMPLETED        = 3

# mongodb connection settings
client = pymongo.MongoClient()
db = client.thug

# Now Importing All Plugins.
available_plugins = {}
for x in PluginBase.__subclasses__():
    available_plugins[x.__name__] = x

logger = logging.getLogger(__name__)


class InvalidMongoIdException(Exception):
    pass

class Command(BaseCommand):
    def fetch_new_tasks(self):
        return Task.objects.filter(plugin_status__exact=STATUS_NEW)

    def get_data(self, task):
        "Retrieves from DB and returns Python Object"
        return db.analysiscombo.find_one(ObjectId(task.object_id))

    def mark_task_as_running(self, task):
        logger.info("[{}] Marking task as running".format(task.id))
        task.started_on = datetime.now(pytz.timezone(settings.TIME_ZONE))
        task.plugin_status = STATUS_PROCESSING
        task.save()

    def mark_task_as_failed(self, task):
        logger.info("[{}] Marking task as failed".format(task.id))
        task.completed_on = datetime.now(pytz.timezone(settings.TIME_ZONE))
        task.plugin_status = STATUS_FAILED
        task.save()

    def mark_task_as_completed(self, task):
        logger.info("[{}] Marking task as completed".format(ptask.id))
        task.completed_on = datetime.now(pytz.timezone(settings.TIME_ZONE))
        task.plugin_status = STATUS_COMPLETED
        task.save()

    def mark_ptask_as_running(self, ptask):
        logger.info("Now running {}".format(ptask.plugin_name))
        ptask.started_on = datetime.now(pytz.timezone(settings.TIME_ZONE))
        ptask.status = STATUS_PROCESSING
        ptask.save()

    def handle(self, *args, **options):
        logger.info("Starting up enrichment daemon")
        while True:
            logger.info("Fetching new tasks requiring enrichment.")
            tasks = self.fetch_new_tasks()
            logger.info("Got {} new tasks for enrichment.".format(len(tasks)))
            for task in tasks:
                data = self.get_data(task)
                self.mark_task_as_running(task)
                ptasks = task.plugintask_set.filter(status=STATUS_NEW)
                task_queue = self.make_ptask_queue(ptasks)
                logger.info("Will run queue of {} plugins for enrichment.".format(len(ptasks)))
                final_data = self.run_ptask_queue(data, task_queue)
                logger.info("Writing results to database.")
                try:
                    self.write_results(task, data)
                    self.mark_task_as_completed(task)
                except:
                    log.debug("FAILED: Unable to write to DB.")
                    self.mark_task_as_failed(task)
            logger.info("Sleeping for {} seconds".format(60))
            time.sleep(60)
