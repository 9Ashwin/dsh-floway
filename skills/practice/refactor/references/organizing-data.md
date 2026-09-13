# Organizing Data

Encapsulate fields and collections, replace primitives and type codes with objects, and choose
between value and reference semantics. Read this when raw data carries meaning that an object
should carry instead.

#### Self Encapsulate Field
Access fields through getters and setters, even within the owning class.

#### Replace Data Value with Object
When a data item needs additional data or behavior, turn it into an object.

**Before:**
```java
class Order {
    private String customer;  // Just a string
}
```

**After:**
```java
class Order {
    private Customer customer;  // Rich object with name, address, credit rating
}
```

#### Change Value to Reference
When you need to share one instance of an object across multiple places.

#### Change Reference to Value
When a reference object is small, immutable, and you want value semantics.

#### Replace Array with Object
When an array holds heterogeneous data (`String[] row = new String[3]` — name, score, wins), replace with an object.

#### Duplicate Observed Data
Domain data lives in a GUI control but domain logic needs it. Copy the data into a domain object and set up an observer to keep the two in sync (Observer pattern). Separates presentation from domain so each can evolve independently.

#### Change Unidirectional Association to Bidirectional
Two classes need each other's features but only one holds a reference. Add a back-pointer and make the modifiers on both ends keep the link consistent. Add the reference only when genuinely needed — bidirectional links raise coupling and risk inconsistency.

#### Change Bidirectional Association to Unidirectional
A two-way link exists but one side no longer uses the other. Drop the unneeded direction. Reduces coupling, simplifies lifecycle management, and avoids "zombie" objects kept alive only by a stale back-pointer.

#### Replace Magic Number with Symbolic Constant
Replace literal numbers/strings with named constants.

#### Encapsulate Field
Make public fields private and provide accessors.

#### Encapsulate Collection
Never return the raw collection. Return a read-only view and provide add/remove methods.

#### Replace Type Code with Class
Replace a numeric/string type code with a class that has meaningful behavior.

#### Replace Type Code with Subclasses
When type code affects behavior, use polymorphism instead of conditionals.

#### Replace Type Code with State/Strategy
Similar to subclasses but uses composition when the type can change at runtime.

#### Replace Subclass with Fields
When subclasses vary only in constant data, replace them with fields on a single class.
