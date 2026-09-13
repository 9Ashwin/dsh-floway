# Simplifying Conditional Expressions and Method Calls

Untangle boolean logic and make the call site read like the intent. Read this when conditionals
nest deeply or branch on type codes, or when names, parameters, and construction make a call
hard to read.

## Simplifying Conditional Expressions

#### Decompose Conditional
Extract the condition, then-part, and else-part into separate methods.

**Before:**
```java
if (date.before(SUMMER_START) || date.after(SUMMER_END)) {
    charge = quantity * _winterRate + _winterServiceCharge;
} else {
    charge = quantity * _summerRate;
}
```

**After:**
```java
if (isSummer(date)) {
    charge = summerCharge(quantity);
} else {
    charge = winterCharge(quantity);
}
```

#### Consolidate Conditional Expression
Combine multiple conditionals that have the same result.

#### Consolidate Duplicate Conditional Fragments
Move code that appears in every branch outside the conditional.

#### Remove Control Flag
Replace control flags with break, continue, or return.

#### Replace Nested Conditional with Guard Clauses
Use early returns for special cases instead of deep nesting.

**Before (arrow code):**
```java
double getPayAmount() {
    double result;
    if (_isDead) {
        result = deadAmount();
    } else {
        if (_isSeparated) {
            result = separatedAmount();
        } else {
            if (_isRetired) {
                result = retiredAmount();
            } else {
                result = normalPayAmount();
            }
        }
    }
    return result;
}
```

**After:**
```java
double getPayAmount() {
    if (_isDead) return deadAmount();
    if (_isSeparated) return separatedAmount();
    if (_isRetired) return retiredAmount();
    return normalPayAmount();
}
```

#### Replace Conditional with Polymorphism
When a conditional chooses different behavior based on the type of an object, use subclasses.

#### Introduce Null Object
Replace null checks with a null object that provides default behavior.

#### Introduce Assertion
State assumptions explicitly with assertions.

## Making Method Calls Simpler

#### Rename Method
The name should say what the method does. If you can't think of a good name, the method may have multiple responsibilities.

#### Add Parameter / Remove Parameter
Add parameters when a method needs more info. Remove parameters when the method can get the info another way.

#### Separate Query from Modifier
A method should either return a value OR change state, never both.

#### Parameterize Method
Several methods doing similar things with different values → one method with a parameter.

#### Replace Parameter with Explicit Methods
The inverse: when a parameter essentially selects different behavior, create separate methods.

#### Preserve Whole Object
Pass the whole object instead of pulling individual fields from it.

#### Replace Parameter with Method
*(refactoring.guru: Replace Parameter with Method Call)* When a parameter can be computed from data the object already has, remove the parameter and let the method call the query itself.

#### Introduce Parameter Object
Group parameters that naturally go together into an object.

#### Remove Setting Method
Make a field immutable by removing its setter and setting it in the constructor.

#### Hide Method
Make methods private when they're not used outside the class.

#### Replace Constructor with Factory Method
When you need more flexibility than a simple constructor call.

#### Replace Error Code with Exception
Throw an exception instead of returning an error code.

#### Replace Exception with Test
Check the condition first instead of catching an exception.
