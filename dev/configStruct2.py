
class A():
    def __init__(self):
        pass

    def setConfig(self, config):
        self.conf = B()
        self.conf.a = config.a
        self.conf.b = config.b
        print self.conf.f

        c = C()
        c.b.a = config.a
        c.b.b = config.b
        print c.b.f

        conf = B()
        conf.a = config.a
        conf.b = config.b
        print conf.f
        print config.f

        self.a = config.a
        self.b = config.b

    def show(self):
        print self.a
        print self.a.c
        print self.f

class B():
    def __init__(self):
        self.a = None

class C():
    def __init__(self):
        self.b = B()

def test():
    b = B()
    b.a = "a"
    b.b = "b"
    #print b.f

    a = A()
    a.setConfig(b)
    a.show()

if __name__=='__main__':
    test()

