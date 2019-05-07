import time
import uuid
import random
import asyncio
import datetime

from aiohttp import test_utils

from tt_web import postgresql as db

from tt_protocol.protocol import timers_pb2

from .. import relations
from .. import operations
from .. import exceptions

from . import helpers


async def create_timer(owner_id, entity_id, type, speed=4.5, border=450, callback_data=None, resources=0):

    if callback_data is None:
        callback_data = 'data_{}_{}_{}'.format(owner_id, entity_id, type)

    result = await operations.create_timer(owner_id=owner_id,
                                           entity_id=entity_id,
                                           type=type,
                                           speed=speed,
                                           border=border,
                                           resources=resources,
                                           callback_data=callback_data)
    return result


class CreateTimerTests(helpers.BaseTests):

    @test_utils.unittest_run_loop
    async def test_success(self):
        timer = await create_timer(1, 2, 3, resources=0)

        results = await db.sql('SELECT * FROM timers')

        self.assertEqual(len(results), 1)

        self.assertEqual(results[0]['owner'], 1)
        self.assertEqual(results[0]['entity'], 2)
        self.assertEqual(results[0]['type'], 3)
        self.assertEqual(results[0]['speed'], 4.5)
        self.assertEqual(results[0]['border'], 450)
        self.assertEqual(results[0]['resources'], 0)
        self.assertEqual(results[0]['finish_at'], results[0]['resources_at'] + datetime.timedelta(seconds=450/4.5))
        self.assertEqual(results[0]['data'], {'callback_data': 'data_1_2_3'})

        self.assertEqual(operations.TIMERS_QUEUE.first(), (timer.id, timer.finish_at))

    @test_utils.unittest_run_loop
    async def test_success__initial_resources(self):
        timer = await create_timer(1, 2, 3, resources=4.5*10)

        results = await db.sql('SELECT * FROM timers')

        self.assertEqual(len(results), 1)

        self.assertEqual(results[0]['owner'], 1)
        self.assertEqual(results[0]['entity'], 2)
        self.assertEqual(results[0]['type'], 3)
        self.assertEqual(results[0]['speed'], 4.5)
        self.assertEqual(results[0]['border'], 450)
        self.assertEqual(results[0]['resources'], 45)
        self.assertEqual(results[0]['finish_at'], results[0]['resources_at'] + datetime.timedelta(seconds=(450-45)/4.5))
        self.assertEqual(results[0]['data'], {'callback_data': 'data_1_2_3'})

        self.assertEqual(operations.TIMERS_QUEUE.first(), (timer.id, timer.finish_at))

    @test_utils.unittest_run_loop
    async def test_already_exists(self):
        timer = await create_timer(1, 2, 3)

        with self.assertRaises(exceptions.TimerAlreadyExists):
            await create_timer(1, 2, 3)

        results = await db.sql('SELECT * FROM timers')

        self.assertEqual(len(results), 1)

        self.assertEqual(len(operations.TIMERS_QUEUE), 1)
        self.assertEqual(operations.TIMERS_QUEUE.first(), (timer.id, timer.finish_at))

    @test_utils.unittest_run_loop
    async def test_multiple_timers(self):
        timer_1 = await create_timer(1, 2, 3)
        timer_2 = await create_timer(10, 20, 30)

        results = await db.sql('SELECT * FROM timers')

        self.assertEqual(len(results), 2)

        self.assertEqual(len(operations.TIMERS_QUEUE), 2)
        self.assertEqual(operations.TIMERS_QUEUE.pop(), (timer_1.id, timer_1.finish_at))
        self.assertEqual(operations.TIMERS_QUEUE.pop(), (timer_2.id, timer_2.finish_at))


class ChangeSpeedTests(helpers.BaseTests):

    @test_utils.unittest_run_loop
    async def test_success(self):
        await create_timer(1, 2, 3, resources=10, speed=10, border=100)

        time.sleep(0.1)

        timer = await operations.change_speed(1, 2, 3, speed=20)

        results = await db.sql('SELECT * FROM timers')

        self.assertEqual(len(results), 1)

        self.assertEqual(timer.owner_id, 1)
        self.assertEqual(timer.entity_id, 2)
        self.assertEqual(timer.type, 3)
        self.assertEqual(timer.speed, 20)
        self.assertEqual(timer.border, 100)
        self.assertEqual(round(timer.resources), 11)

        finish_at_delta = (timer.finish_at - (timer.resources_at + datetime.timedelta(seconds=(100-11)/20))).total_seconds()

        self.assertTrue(abs(finish_at_delta) < 0.01)

        self.assertEqual(operations.TIMERS_QUEUE.first(), (timer.id, timer.finish_at))

        results = await db.sql('SELECT * FROM timers')

        self.assertEqual(len(results), 1)

        self.assertEqual(results[0]['owner'], timer.owner_id)
        self.assertEqual(results[0]['entity'], timer.entity_id)
        self.assertEqual(results[0]['type'], timer.type)
        self.assertEqual(results[0]['speed'], timer.speed)
        self.assertEqual(results[0]['border'], timer.border)
        self.assertEqual(results[0]['resources'], timer.resources)
        self.assertEqual(results[0]['resources_at'].replace(tzinfo=None), timer.resources_at)
        self.assertEqual(results[0]['finish_at'].replace(tzinfo=None), timer.finish_at)
        self.assertEqual(results[0]['data'], {'callback_data': 'data_1_2_3'})

    @test_utils.unittest_run_loop
    async def test_no_timer(self):
        await create_timer(1, 2, 3, resources=10, speed=10, border=100)

        with self.assertRaises(exceptions.TimerNotFound):
            await operations.change_speed(1, 2, 4, speed=20)


class LoadAllTimersTests(helpers.BaseTests):

    @test_utils.unittest_run_loop
    async def test_no_timers(self):
        await operations.load_all_timers()
        self.assertTrue(operations.TIMERS_QUEUE.empty())

    @test_utils.unittest_run_loop
    async def test_has_timers(self):
        timer_1 = await create_timer(1, 2, 3, speed=1)
        timer_2 = await create_timer(10, 2, 3, speed=4)
        timer_3 = await create_timer(1, 20, 3, speed=3)
        timer_4 = await create_timer(1, 2, 30, speed=2)

        operations.TIMERS_QUEUE.clean()

        self.assertTrue(operations.TIMERS_QUEUE.empty())

        await operations.load_all_timers()

        self.assertEqual(len(operations.TIMERS_QUEUE), 4)
        self.assertEqual(operations.TIMERS_QUEUE.pop(), (timer_2.id, timer_2.finish_at))
        self.assertEqual(operations.TIMERS_QUEUE.pop(), (timer_3.id, timer_3.finish_at))
        self.assertEqual(operations.TIMERS_QUEUE.pop(), (timer_4.id, timer_4.finish_at))
        self.assertEqual(operations.TIMERS_QUEUE.pop(), (timer_1.id, timer_1.finish_at))


class FakeScheduler(object):

    def __init__(self):
        self.timers = []

    def __call__(self, callback, timer_id, config):
        self.timers.append(timer_id)


class FinishCompletedTimersTests(helpers.BaseTests):

    @test_utils.unittest_run_loop
    async def test_no_timers(self):
        scheduler = FakeScheduler()

        operations.finish_completed_timers(scheduler, {})

        self.assertEqual(scheduler.timers, [])

    @test_utils.unittest_run_loop
    async def test_has_timers(self):
        timer_1 = await create_timer(1, 2, 3, speed=1)
        timer_2 = await create_timer(10, 2, 3, speed=100000)
        timer_3 = await create_timer(1, 20, 3, speed=10000000000000)
        timer_4 = await create_timer(1, 2, 30, speed=2)

        time.sleep(0.01)

        scheduler = FakeScheduler()

        operations.finish_completed_timers(scheduler, {})

        self.assertEqual(scheduler.timers, [timer_3.id, timer_2.id])

    @test_utils.unittest_run_loop
    async def test_process_all(self):
        timer_1 = await create_timer(1, 2, 3, speed=10000000000000)
        timer_2 = await create_timer(10, 2, 3, speed=100000)
        timer_3 = await create_timer(1, 20, 3, speed=10000000000000)

        time.sleep(0.01)

        scheduler = FakeScheduler()

        operations.finish_completed_timers(scheduler, {})

        self.assertEqual(scheduler.timers, [timer_1.id, timer_3.id, timer_2.id])


class FakeCallback(object):

    def __init__(self, results, delay=0):
        self.calls = []
        self.results = list(results)
        self.delay = delay

    async def __call__(self, **kwargs):
        if self.delay > 0:
            asyncio.sleep(self.delay)

        self.calls.append(kwargs)
        return self.results.pop(0)


class FinishTimerTests(helpers.BaseTests):

    def setUp(self):
        super().setUp()

        self.config = helpers.get_config()['custom']

    @test_utils.unittest_run_loop
    async def test_no_timer(self):
        callback = FakeCallback(results=[(True, relations.POSTPROCESS_TYPE.RESTART)])

        await operations.finish_timer(timer_id=666, config=self.config, callback=callback)

        self.assertEqual(callback.calls, [])

    @test_utils.unittest_run_loop
    async def test_timer_not_finished(self):
        timer = await create_timer(1, 2, 3, speed=0.01)

        callback = FakeCallback(results=[(True, relations.POSTPROCESS_TYPE.RESTART)])

        await operations.finish_timer(timer_id=timer.id, config=self.config, callback=callback)

        self.assertEqual(callback.calls, [])

        self.assertEqual(len(operations.TIMERS_QUEUE), 1)

    @test_utils.unittest_run_loop
    async def test_callback_successed(self):
        timer = await create_timer(1, 2, 3, speed=10000000)

        operations.TIMERS_QUEUE.pop()

        time.sleep(0.01)

        callback = FakeCallback(results=[(True, relations.POSTPROCESS_TYPE.RESTART)])

        async def postprocess(**kwargs):
            pass

        await operations.finish_timer(timer_id=timer.id,
                                      config=self.config,
                                      callback=callback,
                                      postprocess=postprocess)

        self.assertEqual(callback.calls, [{'data': 'data_1_2_3',
                                           'secret': 'test.secret',
                                           'url': 'http://example.com/3',
                                           'timer': timer}])

        self.assertTrue(operations.TIMERS_QUEUE.empty())

    @test_utils.unittest_run_loop
    async def test_race(self):
        timer = await create_timer(1, 2, 3, speed=10000000)

        operations.TIMERS_QUEUE.pop()

        time.sleep(0.01)

        callback = FakeCallback(results=[(True, relations.POSTPROCESS_TYPE.REMOVE),
                                         (True, relations.POSTPROCESS_TYPE.REMOVE)])

        task_1 = operations.finish_timer(timer_id=timer.id,
                                         config=self.config,
                                         callback=callback)

        task_2 = operations.finish_timer(timer_id=timer.id,
                                         config=self.config,
                                         callback=callback)

        await asyncio.gather(task_1, task_2)

        # first call must remove timer
        self.assertEqual(callback.calls, [{'data': 'data_1_2_3',
                                           'secret': 'test.secret',
                                           'url': 'http://example.com/3',
                                           'timer': timer}])

        self.assertTrue(operations.TIMERS_QUEUE.empty())

    @test_utils.unittest_run_loop
    async def test_semaphore(self):

        delays = [0.02, 0.03, 0.05, 0.07, 0.11, 0.13, 0.17, 0.19, 0.23, 0.29]

        timers = []

        for i in range(len(delays)):
            timer = await create_timer(i, 2, 3, speed=10000000)
            timers.append(timer)

        operations.TIMERS_QUEUE.pop()

        time.sleep(0.01)

        storage = set()
        history = []

        def create_callback(delay):
            async def callback(*argv, **kwargs):
                uid = uuid.uuid4().hex
                storage.add(uid)

                self.assertTrue(len(storage) <= 5)

                await asyncio.sleep(delay)

                storage.remove(uid)

                history.append(len(storage))

                return True, relations.POSTPROCESS_TYPE.RESTART

            return callback

        async def postprocess(**kwargs):
            pass

        tasks = []

        random.shuffle(delays)

        for delay, timer in zip(delays, timers):
            task = operations.finish_timer(timer_id=timer.id,
                                           config=self.config,
                                           callback=create_callback(delay),
                                           postprocess=postprocess)
            tasks.append(task)

        await asyncio.gather(*tasks)

        self.assertEqual(storage, set())
        self.assertEqual(history, [4, 4, 4, 4, 4, 4, 3, 2, 1, 0])

    @test_utils.unittest_run_loop
    async def test_callback_failed(self):
        timer = await create_timer(1, 2, 1, speed=10000000)

        operations.TIMERS_QUEUE.pop()

        time.sleep(0.01)

        callback = FakeCallback(results=((False, None),
                                         (False, None),
                                         (True, relations.POSTPROCESS_TYPE.RESTART)))

        async def postprocess(**kwargs):
            pass

        await operations.finish_timer(timer_id=timer.id,
                                      config=self.config,
                                      callback=callback,
                                      postprocess=postprocess)

        self.assertEqual(callback.calls, [{'data': 'data_1_2_1',
                                           'secret': 'test.secret',
                                           'url': 'http://example.com/1',
                                           'timer': timer},
                                          {'data': 'data_1_2_1',
                                           'secret': 'test.secret',
                                           'url': 'http://example.com/1',
                                           'timer': timer},
                                          {'data': 'data_1_2_1',
                                           'secret': 'test.secret',
                                           'url': 'http://example.com/1',
                                           'timer': timer}])

        self.assertTrue(operations.TIMERS_QUEUE.empty())

    @test_utils.unittest_run_loop
    async def test_wrong_type(self):
        timer = await create_timer(1, 2, 666, speed=10000000)

        operations.TIMERS_QUEUE.pop()

        time.sleep(0.01)

        callback = FakeCallback(results=[(True, relations.POSTPROCESS_TYPE.RESTART)])

        async def postprocess(**kwargs):
            pass

        with self.assertRaises(exceptions.WrongTimerType):
            await operations.finish_timer(timer_id=timer.id,
                                          config=self.config,
                                          callback=callback,
                                          postprocess=postprocess)

        self.assertEqual(callback.calls, [])

        self.assertTrue(operations.TIMERS_QUEUE.empty())


class DoCallbackTests(helpers.BaseTests):

    @test_utils.unittest_run_loop
    async def test_wrong_format(self):
        timer = await create_timer(1, 2, 666, speed=10000000)

        operations.TIMERS_QUEUE.pop()

        async def fake_http_caller(*argv):
            return True, b'wrong data'

        success, postprocess_type = await operations.do_callback(secret='test.secret',
                                                                 url='http://example.com/1',
                                                                 timer=timer,
                                                                 data='data_x',
                                                                 http_caller=fake_http_caller)
        self.assertFalse(success)
        self.assertEqual(postprocess_type, None)

    @test_utils.unittest_run_loop
    async def test_remove(self):
        timer = await create_timer(1, 2, 666, speed=10000000)

        operations.TIMERS_QUEUE.pop()

        async def fake_http_caller(*argv):
            data = timers_pb2.CallbackAnswer(postprocess_type=timers_pb2.CallbackAnswer.PostprocessType.Value('REMOVE'))
            return True, data.SerializeToString()

        success, postprocess_type = await operations.do_callback(secret='test.secret',
                                                                 url='http://example.com/1',
                                                                 timer=timer,
                                                                 data='data_x',
                                                                 http_caller=fake_http_caller)
        self.assertTrue(success)
        self.assertEqual(postprocess_type, relations.POSTPROCESS_TYPE.REMOVE)

    @test_utils.unittest_run_loop
    async def test_restart(self):
        timer = await create_timer(1, 2, 666, speed=10000000)

        operations.TIMERS_QUEUE.pop()

        async def fake_http_caller(*argv):
            data = timers_pb2.CallbackAnswer(postprocess_type=timers_pb2.CallbackAnswer.PostprocessType.Value('RESTART'))
            return True, data.SerializeToString()

        success, postprocess_type = await operations.do_callback(secret='test.secret',
                                                                 url='http://example.com/1',
                                                                 timer=timer,
                                                                 data='data_x',
                                                                 http_caller=fake_http_caller)
        self.assertTrue(success)
        self.assertEqual(postprocess_type, relations.POSTPROCESS_TYPE.RESTART)

    @test_utils.unittest_run_loop
    async def test_wrong_command(self):
        timer = await create_timer(1, 2, 666, speed=10000000)

        operations.TIMERS_QUEUE.pop()

        async def fake_http_caller(*argv):
            data = timers_pb2.CallbackAnswer(postprocess_type=111)
            return True, data.SerializeToString()

        success, postprocess_type = await operations.do_callback(secret='test.secret',
                                                                 url='http://example.com/1',
                                                                 timer=timer,
                                                                 data='data_x',
                                                                 http_caller=fake_http_caller)
        self.assertFalse(success)
        self.assertEqual(postprocess_type, None)


class PostprocessRestartTests(helpers.BaseTests):

    @test_utils.unittest_run_loop
    async def test_continue(self):
        timer = await create_timer(1, 2, 3, speed=2, border=10)

        await operations.postprocess_timer(timer.id, relations.POSTPROCESS_TYPE.RESTART)

        results = await db.sql('SELECT * FROM timers WHERE id=%(id)s', {'id': timer.id})

        self.assertEqual(len(results), 1)

        self.assertEqual(results[0]['resources'], 0)
        self.assertEqual(results[0]['resources_at'].replace(tzinfo=None), timer.finish_at)
        self.assertEqual(results[0]['finish_at'].replace(tzinfo=None), timer.finish_at+datetime.timedelta(seconds=10/2))


class PostprocessRemoveTests(helpers.BaseTests):

    @test_utils.unittest_run_loop
    async def test_continue(self):
        timer = await create_timer(1, 2, 3, speed=2, border=10)

        await operations.postprocess_timer(timer.id, relations.POSTPROCESS_TYPE.REMOVE)

        results = await db.sql('SELECT * FROM timers WHERE id=%(id)s', {'id': timer.id})

        self.assertFalse(results)


class GetOwnerTimersTests(helpers.BaseTests):

    @test_utils.unittest_run_loop
    async def test_no_timer(self):
        await create_timer(1, 2, 3)
        await create_timer(2, 2, 3)

        timers = await operations.get_owner_timers(666)

        self.assertEqual(timers, [])

    @test_utils.unittest_run_loop
    async def test_success(self):
        timer_1 = await create_timer(1, 2, 3, speed=10)
        timer_2 = await create_timer(2, 2, 3)
        timer_3 = await create_timer(1, 3, 4, speed=100)

        timers = await operations.get_owner_timers(1)

        self.assertEqual(timers, [timer_3, timer_1])
