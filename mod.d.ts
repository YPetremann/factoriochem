declare let modname: string;

declare const data: any;
declare function type(value: any): string;
declare function pairs<T>(iterable: { [key: string]: T }): LuaIterable<LuaMultiReturn<[string, T]>>;
declare function ipairs<T>(iterable: Array<T>): LuaIterable<LuaMultiReturn<[number, T]>>;
declare function require(name): any;
declare interface Atom {
  row: number;
  col: number;
  symbol: string;
  number: number;
  valency: number;
}
