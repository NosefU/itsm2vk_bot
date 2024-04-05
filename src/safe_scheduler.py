import datetime as dt
import logging
from traceback import format_exc

import schedule


class SafeScheduler(schedule.Scheduler):
    """
    An implementation of Scheduler that catches jobs that fail, logs their
    exception tracebacks as errors, optionally reschedules the jobs for their
    next run time, and keeps going.

    Use this to run jobs that may or may not crash without worrying about
    whether other jobs will run or if they'll crash the entire script.
    """

    def __init__(self, reschedule_on_failure=True, minutes_after_failure=0, seconds_after_failure=0):
        """
        If reschedule_on_failure is True, jobs will be rescheduled for their
        next run as if they had completed successfully. If False, they'll run
        on the next run_pending() tick.
        """
        self.reschedule_on_failure = reschedule_on_failure
        self.minutes_after_failure = minutes_after_failure
        self.seconds_after_failure = seconds_after_failure
        super().__init__()

    def _run_job(self, job):
        try:
            super()._run_job(job)
        except Exception:
            logging.error(format_exc())
            if self.reschedule_on_failure:
                if self.minutes_after_failure != 0 or self.seconds_after_failure != 0:
                    logging.warning("Rescheduled in %s minutes and %s seconds." % (self.minutes_after_failure, self.seconds_after_failure))
                    job.last_run = None
                    job.next_run = dt.datetime.now() + dt.timedelta(minutes=self.minutes_after_failure, seconds=self.seconds_after_failure)
                else:
                    logging.warning("Rescheduled.")
                    job.last_run = dt.datetime.now()
                    job._schedule_next_run()
            else:
                logging.warning("Job canceled.")
                self.cancel_job(job)
