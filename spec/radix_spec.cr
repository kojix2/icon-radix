require "spec"
require "../src/icon/radix"

describe Icon::Radix do
  it "provides standard icons" do
    Icon::Radix::Gear.should_not be_nil
    Icon::Radix::Home.should_not be_nil
  end
end
