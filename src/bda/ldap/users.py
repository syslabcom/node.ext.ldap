from zope.interface import implements
from bda.ldap import LDAPProps, LDAPNode
from bda.ldap import BASE, ONELEVEL, SUBTREE
from bda.ldap.interfaces import ILDAPUsersConfig

class LDAPPrincipal(LDAPNode):
    """Superclass for LDAPUser and LDAPGroup
    """
    @property
    def id(self):
        return self.__name__

class LDAPPrincipals(LDAPNode):
    """Superclass for LDAPUsers and LDAPGroups
    """
    # principals have ids
    ids = LDAPNode.keys

    def __init__(self, cfg):
        super(LDAPPrincipals, self).__init__(name=cfg.baseDN, props=cfg.props)
        self._search_filter = cfg.queryFilter
        self._search_scope = cfg.scope
        self._key_attr = cfg.id_attr

class LDAPUsersConfig(object):
    """Define how users look and where they are
    """
    implements(ILDAPUsersConfig)
    
     #when a user is modified, killed etc an event is emmited. To grab it you must:
    #zope.component.provideHandler(funct_to_be_executed,[1st_arg_objecttype,2nd_arg_objecttype,..])

    def __init__(self,
            props,
            baseDN='',
            id_attr='uid',
            login_attr='uid',
            scope=ONELEVEL,
            queryFilter='(objectClass=inetOrgPerson)'):
        self.props = props
        self.baseDN = baseDN
        self.id_attr = id_attr
        self.login_attr = login_attr
        self.scope = scope
        self.queryFilter = queryFilter

# XXX: hanging out, waiting for a better home
def ldapUsersConfigFromLUF(luf):
    """Create LDAPUsersConfig from an LDAPUserFolder
    """
    server = luf._delegate._servers[0]
    props = self._props = LDAPProps(
            server=server['host'],
            port=int(server['port']),
            user=luf._binduid,
            password=luf._bindpwd,
            )
    uc = LDAPUsersConfig(props,
            baseDN=luf.users_base,
            id_attr=luf.getProperty('_uid_attr'),
            login_attr=luf.getProperty('_login_attr'),
            scope=luf._delegate.getScopes()[luf.users_scope],
            queryFilter=luf._getUserFilterString(),
            )
    return uc

class LDAPUser(LDAPPrincipal):
    """An ldap user

    XXX: should this be a node or an adpater for a node?

    Filtering attributes, eg userPassword and providing a setpassword and
    authenticate method might be good. On the other hand, why to filter out
    userPassword?

    If we want to hide the userpassword from the attrs, we either need
    two-stage __setitem__ on LDAPNodeAttributes or LDAPUsers needs to be
    adapter around a real normal node.
    """
    @property
    def login(self):
        return self.attrs[self.__parent__._login_attr]

    def authenticate(self, pw):
        return self._session.authenticate(self.DN, pw)

    def passwd(self, oldpw, newpw):
        """set a users password
        """
        self._session.passwd(self.DN, oldpw, newpw)

class LDAPUsers(LDAPPrincipals):
    """Manage LDAP users
    """
    def __init__(self, cfg):
        super(LDAPUsers, self).__init__(cfg)
        self._login_attr = cfg.login_attr
        self._ChildClass = LDAPUser
        if self._login_attr != self._key_attr:
            self._seckey_attrs = (cfg.login_attr,)

    def idbylogin(self, login):
        return self._seckeys[self._login_attr][login]

    def authenticate(self, id=None, login=None, pw=None):
        """Authenticate a user either by id xor by login

        If successful, the user's id is returned, otherwise None
        """
        if id is not None and login is not None:
            raise ValueError(u"Either specify id or login, not both.")
        if pw is None:
            raise ValueError(u"You need to specify a password")
        if login:
            if self._login_attr == self._key_attr:
                id = login
            else:
                id = self.idbylogin(login)
        userdn = self.child_dn(id)
        if self._session.authenticate(userdn, pw):
            return id
        else:
            return None

    def passwd(self, id, oldpw, newpw):
        """Change a users password
        """
        self._session.passwd(self.child_dn(id), oldpw, newpw)
