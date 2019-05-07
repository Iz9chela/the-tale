
import smart_imports

smart_imports.all()


class HELP_CHOICES(rels_django.DjangoEnum):
    priority = rels.Column(unique=False)

    records = (('HEAL', 0, 'лечение', 160),
               ('TELEPORT', 1, 'телепорт', 160),
               ('LIGHTING', 2, 'молния', 160),
               ('START_QUEST', 3, 'начало задания', 800),
               ('MONEY', 4, 'деньги', 40),
               ('RESURRECT', 5, 'воскрешение', 800),
               ('EXPERIENCE', 6, 'прозрение', 5),
               ('HEAL_COMPANION', 8, 'лечение спутника', 20))


class ABILITY_TYPE(rels_django.DjangoEnum):
    cost = rels.Column(unique=False)
    description = rels.Column()
    request_attributes = rels.Column(unique=False)

    records = (('HELP', 'help', 'Помочь', c.ANGEL_HELP_COST, 'Попытаться помочь герою, чем бы тот не занимался', ()),
               ('DROP_ITEM', 'drop_item', 'Выбросить предмет', c.ANGEL_DROP_ITEM_COST, 'Выбросить из рюкзака самый ненужный предмет', ()))
