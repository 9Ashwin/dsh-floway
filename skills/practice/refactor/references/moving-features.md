# Moving Features Between Objects and Dealing with Generalization

Move methods and fields to the class that uses them, and reshape the inheritance hierarchy. Read
this when behavior sits in the wrong class, when delegation is too thin or too thick, or when
subclasses and superclasses have drifted apart.

## Moving Features Between Objects

#### Move Method
Move a method to the class where it's used most.

**Mechanics:**
1. Check all features used by the method on its current class
2. Check for polymorphism (subclass/superclass methods)
3. Create the method on the target class, adapting as needed
4. Reference the target object from the source
5. Turn the source method into a delegating method, or remove it
6. Test

#### Move Field
Move a field to the class where it's used most.

#### Extract Class
When a class does the work of two, split it. Create a new class and move relevant fields and methods.

#### Inline Class
When a class does almost nothing, absorb it into the class that uses it most.

#### Hide Delegate
Create methods on the server to hide the delegate chain. `manager = person.getDepartment().getManager()` → `manager = person.getManager()`.

#### Remove Middle Man
When a class is doing too much delegation, call the delegate directly.

#### Introduce Foreign Method
When a server class needs an additional method but you can't modify it, create a method on the client with the server instance as the first argument.

#### Introduce Local Extension
When you need multiple foreign methods, create an extension class (subclass or wrapper).

## Dealing with Generalization

#### Pull Up Field/Method/Constructor Body
Move identical fields/methods/constructor code from subclasses to superclass.

#### Push Down Method/Field
Move behavior from superclass to only the subclasses that use it.

#### Extract Subclass
Create a subclass for a subset of features used in some instances.

#### Extract Superclass
Create a superclass for shared features of similar classes.

#### Extract Interface
Create an interface from a subset of a class's public methods.

#### Collapse Hierarchy
Merge a superclass and subclass when they're not different enough.

#### Form Template Method
Generalize an algorithm in the superclass, letting subclasses fill in the specifics.

#### Replace Inheritance with Delegation
When a subclass only uses part of the superclass, use composition instead.

#### Replace Delegation with Inheritance
When a delegating class needs access to all of the delegate's behavior.
