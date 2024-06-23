from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from cryptography.fernet import Fernet

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    email = Column(String)
    verified = Column(Boolean, default=False)
    public_key = Column(String)
    private_key = Column(String)
    rpc = Column(String)
    slippage = Column(String)
    priority = Column(String)

class UserManager:
    def __init__(self, encryption_key):
        self.cipher_suite = Fernet(encryption_key)
        self.engine = create_engine(os.getenv('DATABASE_URL'))
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def is_user_verified(self, telegram_id):
        session = self.Session()
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        session.close()
        return user.verified if user else False
    
    def has_wallet(self, telegram_id):
        session = self.Session()
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        session.close()
        return bool(user and user.public_key and user.private_key)
    
    def get_wallet(self, telegram_id):
        session = self.Session()
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        session.close()
        if user:
            return {'public_key': user.public_key, 'private_key': self.cipher_suite.decrypt(user.private_key.encode()).decode()}
        return None
    
    def save_wallet(self, telegram_id, wallet):
        session = self.Session()
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.public_key = wallet['public_key']
            user.private_key = self.cipher_suite.encrypt(wallet['private_key'].encode()).decode()
        else:
            user = User(
                telegram_id=telegram_id,
                public_key=wallet['public_key'],
                private_key=self.cipher_suite.encrypt(wallet['private_key'].encode()).decode()
            )
            session.add(user)
        session.commit()
        session.close()
    
    def generate_verification_code(self, telegram_id, email):
        # Generate and store the verification code
        verification_code = "123456"  # Implement your code generation logic
        session = self.Session()
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.email = email
        else:
            user = User(telegram_id=telegram_id, email=email)
            session.add(user)
        session.commit()
        session.close()
        return verification_code
    
    def verify_user(self, telegram_id):
        session = self.Session()
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.verified = True
            session.commit()
        session.close()
    
    def get_private_key(self, telegram_id):
        session = self.Session()
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        session.close()
        if user:
            return self.cipher_suite.decrypt(user.private_key.encode()).decode()
        return None
    
    def update_rpc(self, telegram_id, rpc):
        session = self.Session()
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.rpc = rpc
            session.commit()
        session.close()
    
    def update_slippage(self, telegram_id, slippage):
        session = self.Session()
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.slippage = slippage
            session.commit()
        session.close()
    
    def update_priority(self, telegram_id, priority):
        session = self.Session()
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.priority = priority
            session.commit()
        session.close()
