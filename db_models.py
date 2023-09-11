from inc import *

# ** generating db context
bolt_db = SQLAlchemy()

# ** db model for spotify items
class item(bolt_db.Model):
  id  = bolt_db.Column(bolt_db.Integer, primary_key=True)
  Name = bolt_db.Column(bolt_db.String(50))
  Type = bolt_db.Column(bolt_db.String(50))
  itemSid = bolt_db.Column(bolt_db.String(50))
  Path = bolt_db.Column(bolt_db.String(100))
  Progress = bolt_db.Column(bolt_db.String(10), default="0")
  Total =bolt_db.Column(bolt_db.String(10), default="0")
  boltId = bolt_db.Column(bolt_db.String(50))
  isCompleted = bolt_db.Column(bolt_db.Boolean, default=False)
  timeOfGen = bolt_db.Column(bolt_db.Integer, default=round(time.time()))
  isDisabled = bolt_db.Column(bolt_db.Boolean, default=False)
  Songs = bolt_db.relationship('song', backref='item')

# ** db model for songs
class song(bolt_db.Model):
  id  = bolt_db.Column(bolt_db.Integer, primary_key=True)
  itemId = bolt_db.Column(bolt_db.Integer, bolt_db.ForeignKey('item.id'))
  Name = bolt_db.Column(bolt_db.String(100))
  Artist = bolt_db.Column(bolt_db.String(50))
  Album = bolt_db.Column(bolt_db.String(50))
  Year = bolt_db.Column(bolt_db.String(50))
  Cover = bolt_db.Column(bolt_db.String(1000))
  Genre = bolt_db.Column(bolt_db.String(100))
  trackSid = bolt_db.Column(bolt_db.String(50))
  Status = bolt_db.Column(bolt_db.String(50), default="PENDING")

