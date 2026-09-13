# Composing Methods

Extract, inline, and rename pieces of a method until each name explains its purpose. Read this
when a method is too long, a temporary variable obscures intent, or a parameter is being
reassigned.

#### Extract Method
Turn a code fragment into a method whose name explains its purpose.

**Mechanics:**
1. Create a new method named after what the fragment does (not how)
2. Copy the extracted code into the new method
3. Identify local variables: read-only become parameters, modified become return values
4. Pass parameters and handle return values
5. Replace the original fragment with a call to the new method
6. Test

**Before:**
```java
void printOwing() {
    printBanner();
    // Print details
    System.out.println("name: " + _name);
    System.out.println("amount: " + getOutstanding());
}
```

**After:**
```java
void printOwing() {
    printBanner();
    printDetails(getOutstanding());
}

void printDetails(double outstanding) {
    System.out.println("name: " + _name);
    System.out.println("amount: " + outstanding);
}
```

#### Inline Method
Replace a method call with its body when the method body is as clear as the name.

**Mechanics:**
1. Check the method is not polymorphic (no subclasses override it)
2. Find all callers
3. Replace each call with the method body
4. Delete the method definition
5. Test

#### Extract Variable
Put the result of an expression (or part of it) in a self-explanatory variable.

**Before:**
```java
if (platform.toUpperCase().indexOf("MAC") > -1 &&
    browser.toUpperCase().indexOf("IE") > -1 &&
    wasInitialized() && resize > 0) {
    // ...
}
```

**After:**
```java
final boolean isMacOs = platform.toUpperCase().indexOf("MAC") > -1;
final boolean isIEBrowser = browser.toUpperCase().indexOf("IE") > -1;
final boolean wasResized = resize > 0;
if (isMacOs && isIEBrowser && wasInitialized() && wasResized) {
    // ...
}
```

#### Inline Temp
Replace a temp variable with its expression when the temp is only used once and the expression is clear.

#### Replace Temp with Query
Extract the expression into a method. Temps that are computed once and reused are replaced with method calls.

#### Split Temporary Variable
A temp assigned more than once (not loop/collecting) should be split into separate variables, one per responsibility.

#### Remove Assignments to Parameters
Don't assign to parameters. Use a local variable instead.

#### Replace Method with Method Object
When a long method uses many local variables that make Extract Method hard, turn the method into its own class, with locals as fields.

#### Substitute Algorithm
Replace an algorithm with a clearer one.
